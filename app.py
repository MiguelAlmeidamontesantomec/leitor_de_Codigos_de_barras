import cv2
from pyzbar.pyzbar import decode
from collections import defaultdict
from fpdf import FPDF
from datetime import datetime
import re
import os
import base64
from flask import Flask, render_template, Response, redirect, url_for, jsonify
from gtts import gTTS
import pygame
import threading

app = Flask(__name__)

class BarcodeApp:
    def __init__(self):
        self.barcode_data = defaultdict(int)
        self.capture = cv2.VideoCapture(0)
        self.running = True
        pygame.mixer.init()

    def process_frame(self):
        while self.running:
            ret, frame = self.capture.read()
            if not ret:
                continue

            barcodes = decode(frame)
            for barcode in barcodes:
                barcode_info = barcode.data.decode('utf-8')

                # Validar se o código segue o padrão alfanumérico de 13 caracteres
                if re.fullmatch(r'[A-Za-z0-9]{13}', barcode_info):
                    if self.barcode_data[barcode_info] == 0:
                        self.barcode_data[barcode_info] += 1
                        count = len(self.barcode_data)
                        print(f"Código: {barcode_info}, Total: {count}")
                        
                        # Tocar o som baseado na contagem
                        self.play_sound(count)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = base64.b64encode(buffer).decode('utf-8')
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + base64.b64decode(frame) + b'\r\n\r\n')

    def play_sound(self, count):
        # Usar gTTS para criar o áudio
        tts = gTTS(text=str(count), lang='pt')
        filename = f"count_{count}.mp3"
        tts.save(filename)
        
        # Tocar o som usando pygame
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

    def save_to_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Contagem de Códigos de Barras", ln=True, align='C')
        pdf.ln(10)

        # Cabeçalhos da tabela
        pdf.set_font("Arial", size=10)
        pdf.cell(60, 10, txt="Código", border=1)
        pdf.cell(60, 10, txt="Quantidade", border=1)
        pdf.cell(60, 10, txt="Data", border=1)
        pdf.cell(60, 10, txt="Hora", border=1)
        pdf.ln()

        total_codes = 0
        last_date = None
        for barcode, count in self.barcode_data.items():
            pdf.cell(60, 10, txt=barcode, border=1)
            pdf.cell(60, 10, txt=str(count), border=1)
            now = datetime.now()
            pdf.cell(60, 10, txt=now.strftime("%Y-%m-%d"), border=1)
            pdf.cell(60, 10, txt=now.strftime("%H:%M:%S"), border=1)
            pdf.ln()
            total_codes += count
            last_date = now

        pdf.set_font("Arial", size=12, style='B')
        pdf.cell(60, 10, txt="Total", border=1)
        pdf.cell(60, 10, txt=str(total_codes), border=1)
        pdf.cell(60, 10, txt="", border=1)
        pdf.cell(60, 10, txt="", border=1)
        pdf.ln()

        filename = f"contagem_de_codigos_{last_date.strftime('%Y%m%d_%H%M%S')}.pdf" if last_date else "contagem_de_codigos.pdf"
        pdf.output(filename)

    def list_pdfs(self):
        return [f for f in os.listdir() if f.endswith('.pdf')]

barcode_app = BarcodeApp()

@app.route('/')
def index():
    return render_template('index.html', barcode_count=len(barcode_app.barcode_data))

@app.route('/video_feed')
def video_feed():
    return Response(barcode_app.process_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/save_pdf')
def save_pdf():
    barcode_app.save_to_pdf()
    return redirect(url_for('index'))

@app.route('/list_pdfs')
def list_pdfs():
    pdf_files = barcode_app.list_pdfs()
    return render_template('list_pdfs.html', pdf_files=pdf_files)

@app.route('/stop')
def stop():
    barcode_app.running = False
    barcode_app.capture.release()
    return redirect(url_for('index'))

@app.route('/get_count')
def get_count():
    return jsonify({'count': len(barcode_app.barcode_data)})

if __name__ == '__main__':
    app.run(debug=True)
