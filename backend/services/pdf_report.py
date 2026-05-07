from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
import io

BRAND_BLUE = colors.HexColor('#1F4E79')
LIGHT_BLUE = colors.HexColor('#2E75B6')

def generate_report_pdf(report: dict, questions: list, evaluations: list,
                         candidate_name: str) -> bytes:
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # Title block
    story.append(Paragraph('INTERVUE.AI — Interview Report', ParagraphStyle(
        'title', fontSize=22, textColor=BRAND_BLUE, spaceAfter=6)))
    story.append(Paragraph(f'Candidate: {candidate_name}', styles['Normal']))
    story.append(Paragraph(
        f"Score: {report.get('overall_score', 0)}/100  |  Grade: {report.get('grade', 'N/A')}  |  {report.get('interview_readiness', '')}",
        ParagraphStyle('meta', fontSize=11, textColor=LIGHT_BLUE, spaceAfter=12)))
    story.append(Spacer(1, 0.4*cm))

    # Per-question breakdown
    story.append(Paragraph('Question Breakdown', ParagraphStyle(
        'h2', fontSize=14, textColor=BRAND_BLUE, spaceAfter=6)))

    for i, (q, e) in enumerate(zip(questions, evaluations)):
        story.append(Paragraph(f"Q{i+1}: {q['question']}",
            ParagraphStyle('q', fontSize=10, spaceAfter=3)))
        data = [['Metric', 'Score'],
                ['Overall', str(e.get('score', 0))],
                ['Accuracy', str(e.get('accuracy', 0))],
                ['Clarity', str(e.get('clarity', 0))],
                ['Depth', str(e.get('depth', 0))]]
        t = Table(data, colWidths=[6*cm, 3*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BRAND_BLUE),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        story.append(t)
        story.append(Paragraph(f"Feedback: {e.get('feedback', '')}",
            ParagraphStyle('fb', fontSize=9, textColor=colors.grey, spaceAfter=12)))

    # Improvement plan
    story.append(Paragraph('3-Week Improvement Plan', ParagraphStyle(
        'h2', fontSize=14, textColor=BRAND_BLUE, spaceAfter=6)))
    week_plan = report.get('week_plan', {})
    for wk, plan in week_plan.items():
        story.append(Paragraph(f'{wk.upper()}: {plan}',
            ParagraphStyle('wp', fontSize=10, spaceAfter=4)))

    doc.build(story)
    return buffer.getvalue()