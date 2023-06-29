from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from .models import Student, Tuition

def generate_student_report():
    # Fetch all students and their installments
    students = Student.objects.all()

    # Set up the document
    doc = SimpleDocTemplate("student_report.pdf", pagesize=letter)
    elements = []

    # Define table styles
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
    ])

    # Create table data
    data = []
    data.append(['Name', 'National Number', 'Age', 'Gender', 'Date of Birth', 'Total Tuition', 'Total Payments', 'Remaining Dues'])
    for student in students:
        installments = Tuition.objects.filter(student=student)
        total_tuition = student.total_tuition()
        total_payments = student.total_payments
        remaining_dues = student.remaining_dues()
        data.append([
            student.name,
            student.national_number,
            student.age,
            student.gender,
            student.date_of_birth,
            total_tuition,
            total_payments,
            remaining_dues,
        ])

        # Add installment details
        if installments:
            installment_data = [
                ['Installment Number', 'Amount', 'Paid', 'Receipt Date']
            ]
            for installment in installments:
                installment_data.append([
                    installment.installment_number,
                    installment.amount,
                    installment.paid,
                    installment.receipt_date,
                ])
            elements.append(Paragraph(f"Installments for {student.name}:", getSampleStyleSheet()['Heading3']))
            installment_table = Table(installment_data)
            installment_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ]))
            elements.append(installment_table)

    # Create the table and apply styles
    table = Table(data)
    table.setStyle(style)

    # Add the table to the elements list
    elements.append(table)

    # Build the report
    doc.build(elements)
