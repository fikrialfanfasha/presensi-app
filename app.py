from flask import Flask, render_template, request, redirect, url_for
import csv
import os
from datetime import datetime

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
    current_date = datetime.now().strftime('%d-%m-%Y')
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
    current_month = datetime.now().strftime('%Y-%m')
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

    print("Student Attendance Data:", student_attendance)

    return render_template('rekapan.html', students=students, current_month=current_month, days=days, student_attendance=student_attendance)

if __name__ == '__main__':
    app.run(debug=True)
