from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import PyPDF2
import docx
import os
import tempfile
from gtts import gTTS
import io
import traceback
import requests
import json

app = Flask(__name__)
CORS(app)

# Supported languages with their codes
SUPPORTED_LANGUAGES = {
    'english': 'en',
    'hindi': 'hi',
    'telugu': 'te',
    'british english': 'en',
    'spanish': 'es',
    'chinese': 'zh',
    'korean': 'ko'
}

class DocumentProcessor:
    def __init__(self):
        pass
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            print(f"Extracting text from PDF: {file_path}")
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            print(f"Extracted {len(text)} characters from PDF")
            
            # If no text found, provide helpful message
            if len(text.strip()) < 10:
                text = "This PDF appears to be image-based or protected. Please try a text-based PDF or document file."
            
            return text
            
        except Exception as e:
            error_msg = f"Error reading PDF: {str(e)}"
            print(error_msg)
            return "Unable to extract text from this PDF file. It may be image-based or protected."
    
    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            print(f"Extracting text from DOCX: {file_path}")
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text += paragraph.text + "\n"
            print(f"Extracted {len(text)} characters from DOCX")
            return text
        except Exception as e:
            error_msg = f"Error reading DOCX: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)
    
    def extract_text_from_txt(self, file_path):
        """Extract text from TXT file"""
        try:
            print(f"Extracting text from TXT: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            print(f"Extracted {len(text)} characters from TXT")
            return text
        except Exception as e:
            error_msg = f"Error reading TXT file: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)
    
    def translate_text(self, text, target_language):
        """Translate text to target language using MyMemory API"""
        try:
            print(f"Translating {len(text)} characters to {target_language}")
            
            # Get language code
            lang_code = SUPPORTED_LANGUAGES.get(target_language.lower(), 'en')
            print(f"Using language code: {lang_code}")
            
            if not text or len(text.strip()) == 0:
                return "No text available for translation"
            
            # Check if it's an error message about PDF
            if "image-based" in text.lower() or "protected" in text.lower() or "unable to extract" in text.lower():
                return "Cannot translate: " + text
            
            # Use MyMemory Translation API as fallback
            return self.translate_with_mymemory(text, lang_code)
            
        except Exception as e:
            error_msg = f"Translation error: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return f"Translation failed: {str(e)}"
    
    def translate_with_mymemory(self, text, target_lang):
        """Translate using MyMemory API"""
        try:
            # MyMemory Translation API
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text,
                'langpair': f'en|{target_lang}'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if response.status_code == 200 and data['responseStatus'] == 200:
                translated_text = data['responseData']['translatedText']
                print(f"Translation successful: {translated_text[:100]}...")
                return translated_text
            else:
                return f"Translation API error: {data.get('responseDetails', 'Unknown error')}"
                
        except Exception as e:
            print(f"MyMemory API failed: {e}")
            # Fallback: return the original text with a note
            return f"[Translation unavailable] {text}"
    
    def text_to_speech(self, text, language, filename):
        """Convert text to speech with female voice"""
        try:
            print(f"Converting text to speech for {language}")
            lang_code = SUPPORTED_LANGUAGES.get(language.lower(), 'en')
            
            # Don't try to generate speech for error messages
            if "cannot translate" in text.lower() or "translation failed" in text.lower():
                raise Exception("Cannot generate speech for error messages")
            
            # gTTS uses female voice by default for most languages
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(filename)
            print(f"Speech saved to: {filename}")
            return filename
        except Exception as e:
            error_msg = f"Text-to-speech error: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)

document_processor = DocumentProcessor()

@app.route('/')
def home():
    """Serve the main HTML page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Handle document upload and processing"""
    try:
        print("=== UPLOAD REQUEST RECEIVED ===")
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        target_language = request.form.get('language', 'english')
        
        print(f"File: {file.filename}")
        print(f"Target language: {target_language}")
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        print(f"File saved to: {temp_path}")
        
        # Extract text based on file type
        file_extension = os.path.splitext(file.filename)[1].lower()
        print(f"File extension: {file_extension}")
        
        if file_extension == '.pdf':
            extracted_text = document_processor.extract_text_from_pdf(temp_path)
        elif file_extension == '.docx':
            extracted_text = document_processor.extract_text_from_docx(temp_path)
        elif file_extension == '.txt':
            extracted_text = document_processor.extract_text_from_txt(temp_path)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        # Translate text
        translated_text = document_processor.translate_text(extracted_text, target_language)
        
        response_data = {
            'original_text': extracted_text[:1000] + '...' if len(extracted_text) > 1000 else extracted_text,
            'translated_text': translated_text[:1000] + '...' if len(translated_text) > 1000 else translated_text,
            'language': target_language,
            'original_length': len(extracted_text),
            'translated_length': len(translated_text)
        }
        
        print("=== TRANSLATION COMPLETED ===")
        return jsonify(response_data)
    
    except Exception as e:
        print(f"=== ERROR: {str(e)} ===")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/text-to-speech', methods=['POST'])
def convert_to_speech():
    """Convert translated text to speech"""
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'english')
        
        print(f"TTS Request - Language: {language}, Text length: {len(text)}")
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Don't try to generate speech for error messages
        if "cannot translate" in text.lower() or "translation failed" in text.lower() or "image-based" in text.lower():
            return jsonify({'error': 'Cannot generate speech: ' + text}), 400
        
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            audio_path = temp_audio.name
        
        # Convert to speech
        document_processor.text_to_speech(text, language, audio_path)
        
        return send_file(
            audio_path,
            as_attachment=True,
            download_name='translated_speech.mp3',
            mimetype='audio/mpeg'
        )
    
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/languages', methods=['GET'])
def get_languages():
    """Get list of supported languages"""
    return jsonify({
        'languages': list(SUPPORTED_LANGUAGES.keys())
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)