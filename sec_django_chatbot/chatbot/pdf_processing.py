import PyPDF2

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfFileReader(file)
        text = ''
        for page_num in range(pdf_reader.numPages):
            page = pdf_reader.getPage(page_num)
            text += page.extract_text()
    return text

# PDF 파일 경로를 지정하여 텍스트 추출
pdf_path = 'your_pdf_file.pdf'
text = extract_text_from_pdf(pdf_path)
print(text)
