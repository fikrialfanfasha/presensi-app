from flask import Flask, render_template, request, redirect, url_for, send_file
import csv
import os
from datetime import datetime
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.styles import Border, Side, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

app = Flask(__name__)

def load_students():
    students = []
    with open('data/students.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            students.append({'nis': row['NIS'], 'nama': row['Nama']})
    return students

def save_attendance(attendance):
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f'data/attendance_{date_str}.csv'
    with open(filename, mode='w', newline='') as csvfile:
        fieldnames = ['Tanggal', 'NIS', 'Nama', 'Kehadiran']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in attendance:
            item['Tanggal'] = date_str
            writer.writerow(item)

def load_attendance():
    attendance_records = []
    for file in os.listdir('data'):
        if file.startswith('attendance_') and file.endswith('.csv'):
            with open(f'data/{file}', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    attendance_records.append(row)
    return attendance_records

@app.route('/', methods=['GET', 'POST'])
def index():
    students = load_students()
    current_date = datetime.now().strftime('%d %B %Y')  
    file_exists = os.path.isfile(f'data/attendance_{datetime.now().strftime("%Y-%m-%d")}.csv')
    
    if request.method == 'POST' and not file_exists:
        attendance = []
        for student in students:
            status = request.form.get(f'attendance_{student["nis"]}', 'Hadir')
            attendance.append({'NIS': student['nis'], 'Nama': student['nama'], 'Kehadiran': status})
        save_attendance(attendance)
        return redirect(url_for('index'))
    
    return render_template('index.html', students=students, current_date=current_date, file_exists=file_exists)

@app.route('/rekapan')
def rekapan():
    current_month = datetime.now().strftime('%B %Y')  
    attendance_records = load_attendance()
    students = load_students()
    days = [f'{i:02}' for i in range(1, 32)]

    student_attendance = {}
    for student in students:
        nis = student['nis']
        student_attendance[nis] = {}
        for day in days:
            student_attendance[nis][day] = None

    for record in attendance_records:
        if 'Tanggal' in record:
            record_date = record['Tanggal'][8:10]
            nis = record['NIS']
            if nis in student_attendance:
                student_attendance[nis][record_date] = record['Kehadiran']

    return render_template('rekapan.html', students=students, current_month=current_month, days=days, student_attendance=student_attendance)

@app.route('/export_excel')
def export_excel():
    current_month = datetime.now().strftime('%B_%Y')  # Nama bulan dan tahun
    attendance_records = load_attendance()
    students = load_students()
    days = [f'{i:02}' for i in range(1, 32)]

    student_attendance = {}
    for student in students:
        nis = student['nis']
        student_attendance[nis] = {}
        for day in days:
            student_attendance[nis][day] = None

    for record in attendance_records:
        if 'Tanggal' in record:
            record_date = record['Tanggal'][8:10]
            nis = record['NIS']
            if nis in student_attendance:
                student_attendance[nis][record_date] = record['Kehadiran']

    data = []
    for student in students:
        row = {'NIS': student['nis'], 'Nama Siswa': student['nama']}
        for day in days:
            header = f'{day}/{datetime.now().strftime("%m")}'
            row[header] = student_attendance[student['nis']].get(day, '')
        data.append(row)
    
    df = pd.DataFrame(data)

    wb = Workbook()
    ws = wb.active
    ws.title = "Rekapan Absensi"

    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            cell.alignment = Alignment(horizontal='center', vertical='center')

    ws.column_dimensions['B'].width = 30
    for col in ws.columns:
        max_length = max(len(str(cell.value)) for cell in col)
        adjusted_width = (max_length + 2)
        ws.column_dimensions[col[0].column_letter].width = adjusted_width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f'rekapan_absensi_XI_RPL_2_{current_month}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


if __name__ == '__main__':
    app.run(debug=True)
