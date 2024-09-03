from flask import Flask, render_template, request, redirect, url_for, session, send_file
import csv
import os
from datetime import datetime
import pandas as pd
import io
import calendar
import locale
from openpyxl import Workbook
from openpyxl.styles import Border, Side, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['TEMPLATES_AUTO_RELOAD'] = True
locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')

DATA_FOLDER = 'data'
ATTENDANCE_FOLDER = os.path.join(DATA_FOLDER, 'attendance')
USERS_FILE = os.path.join(DATA_FOLDER, 'users.csv')

if not os.path.exists(ATTENDANCE_FOLDER):
    os.makedirs(ATTENDANCE_FOLDER)

def load_users():
    users = {}
    with open(USERS_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            users[row['username']] = row['password']
    return users
def load_students():
    students = []
    with open(os.path.join(DATA_FOLDER, 'students.csv'), newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            students.append({
                'nis': row['NIS'],
                'nama': row['Nama'],
                'jenis_kelamin': row['Jenis Kelamin'],
                'kelas': row['Kelas']
            })
    return students

def save_attendance(attendance, kelas):
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f'attendance_{kelas}_{date_str}.csv'
    filepath = os.path.join(ATTENDANCE_FOLDER, filename)
    with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Tanggal', 'Kelas', 'NIS', 'Nama', 'Kehadiran']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in attendance:
            item['Tanggal'] = date_str
            item['Kelas'] = kelas
            writer.writerow(item)

def load_attendance():
    attendance_records = []
    for file in os.listdir(ATTENDANCE_FOLDER):
        if file.startswith('attendance_') and file.endswith('.csv'):
            with open(os.path.join(ATTENDANCE_FOLDER, file), newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    attendance_records.append(row)
    return attendance_records

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    students = load_students()
    current_date = datetime.now().strftime('%A, %d %B %Y')
    classes = sorted(set(student['kelas'] for student in students))
    selected_class = request.args.get('kelas', classes[0])  # Default ke kelas pertama
    filtered_students = [s for s in students if s['kelas'] == selected_class]
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    attendance_file = os.path.join(ATTENDANCE_FOLDER, f'attendance_{selected_class}_{date_str}.csv')
    file_exists = os.path.isfile(attendance_file)
    
    if request.method == 'POST' and not file_exists:
        attendance = []
        for student in filtered_students:
            status = request.form.get(f'attendance_{student["nis"]}', 'Hadir')
            attendance.append({
                'NIS': student['nis'],
                'Nama': student['nama'],
                'Kehadiran': status
            })
        save_attendance(attendance, selected_class)
        return redirect(url_for('index', kelas=selected_class))
    
    return render_template('index.html', 
                           students=filtered_students, 
                           classes=classes, 
                           current_date=current_date, 
                           selected_class=selected_class, 
                           file_exists=file_exists)

@app.route('/rekapan')
def rekapan():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    students = load_students()
    attendance_records = load_attendance()
    classes = sorted(set(student['kelas'] for student in students))
    selected_class = request.args.get('kelas', classes[0])
    filtered_students = [s for s in students if s['kelas'] == selected_class]
    
    current_month = datetime.now().strftime('%B %Y')
    year = datetime.now().year
    month = datetime.now().month
    num_days = calendar.monthrange(year, month)[1]
    days = [f'{i:02}' for i in range(1, num_days + 1)]
    
    # Inisialisasi absensi per siswa
    student_attendance = {}
    for student in filtered_students:
        nis = student['nis']
        student_attendance[nis] = {day: '' for day in days}
    
    # Mengisi absensi
    for record in attendance_records:
        if record['Kelas'] != selected_class:
            continue
        record_date = datetime.strptime(record['Tanggal'], '%Y-%m-%d').strftime('%d')
        if record_date in student_attendance.get(record['NIS'], {}):
            student_attendance[record['NIS']][record_date] = record['Kehadiran']
    
    return render_template('rekapan.html', 
                           students=filtered_students, 
                           current_month=current_month, 
                           days=days, 
                           student_attendance=student_attendance, 
                           classes=classes, 
                           selected_class=selected_class)

@app.route('/export_excel')
def export_excel():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    students = load_students()
    attendance_records = load_attendance()
    classes = sorted(set(student['kelas'] for student in students))
    selected_class = request.args.get('kelas', classes[0])
    filtered_students = [s for s in students if s['kelas'] == selected_class]
    
    current_month = datetime.now().strftime('%B_%Y')
    year = datetime.now().year
    month = datetime.now().month
    num_days = calendar.monthrange(year, month)[1]
    days = [f'{i:02}' for i in range(1, num_days + 1)]
    
    # Inisialisasi absensi per siswa
    student_attendance = {}
    for student in filtered_students:
        nis = student['nis']
        student_attendance[nis] = {day: '' for day in days}
    
    # Mengisi absensi
    for record in attendance_records:
        if record['Kelas'] != selected_class:
            continue
        record_date = datetime.strptime(record['Tanggal'], '%Y-%m-%d').strftime('%d')
        if record_date in student_attendance.get(record['NIS'], {}):
            student_attendance[record['NIS']][record_date] = record['Kehadiran']
    
    # Menyiapkan data untuk Excel
    data = []
    for student in filtered_students:
        row = {
            'NIS': student['nis'],
            'Nama Siswa': student['nama']
        }
        for day in days:
            header = f'{day}/{month:02}'
            row[header] = student_attendance[student['nis']].get(day, '')
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Membuat Workbook Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekapan Absensi"
    
    # Menambahkan data ke worksheet
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
    
    # Menyesuaikan lebar kolom
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        adjusted_width = (max_length + 2)
        ws.column_dimensions[col[0].column_letter].width = adjusted_width
    
    # Menyimpan workbook ke dalam BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'rekapan_absensi_{selected_class}_{current_month}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Username atau password salah.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
