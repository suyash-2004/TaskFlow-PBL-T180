import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import g4f
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from app.models import TaskInDB, TaskSummary, ProductivityMetrics, ReportCreate

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.gpt_model = os.getenv("GPT_MODEL", "gpt-3.5-turbo")
    
    def calculate_metrics(self, tasks: List[TaskSummary]) -> ProductivityMetrics:
        """Calculate productivity metrics based on task data."""
        if not tasks:
            return ProductivityMetrics(
                completion_rate=0.0,
                on_time_rate=0.0,
                avg_delay=0.0,
                productivity_score=0.0,
                total_scheduled_time=0,
                total_actual_time=0,
                time_efficiency=0.0
            )
        
        # Count completed tasks
        completed_tasks = [t for t in tasks if t.status == "completed"]
        completion_rate = (len(completed_tasks) / len(tasks)) * 100 if tasks else 0
        
        # Count on-time tasks (no delay or negative delay)
        on_time_tasks = [t for t in completed_tasks if t.delay is not None and t.delay <= 0]
        on_time_rate = (len(on_time_tasks) / len(completed_tasks)) * 100 if completed_tasks else 0
        
        # Calculate average delay
        delays = [t.delay for t in completed_tasks if t.delay is not None]
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        # Calculate total times
        total_scheduled_time = sum(t.scheduled_duration for t in tasks)
        total_actual_time = sum(t.actual_duration for t in completed_tasks if t.actual_duration is not None)
        
        # Calculate time efficiency
        time_efficiency = total_scheduled_time / total_actual_time if total_actual_time > 0 else 0
        
        # Calculate productivity score (custom formula)
        # 50% based on completion rate, 30% based on on-time rate, 20% based on time efficiency
        productivity_score = (
            (completion_rate * 0.5) +
            (on_time_rate * 0.3) +
            (min(time_efficiency, 1) * 100 * 0.2)
        )
        
        return ProductivityMetrics(
            completion_rate=round(completion_rate, 1),
            on_time_rate=round(on_time_rate, 1),
            avg_delay=round(avg_delay, 1),
            productivity_score=round(productivity_score, 1),
            total_scheduled_time=total_scheduled_time,
            total_actual_time=total_actual_time,
            time_efficiency=round(time_efficiency, 2)
        )
    
    def prepare_task_summaries(self, tasks: List[TaskInDB]) -> List[TaskSummary]:
        """Convert TaskInDB objects to TaskSummary objects."""
        task_summaries = []
        
        for task in tasks:
            # Make sure we have scheduled times - add defaults if missing
            scheduled_start = task.scheduled_start_time
            scheduled_end = task.scheduled_end_time
            
            if not scheduled_start or not scheduled_end:
                # Generate default scheduling for report
                now = datetime.now()
                today = datetime.combine(now.date(), datetime.min.time())
                scheduled_start = today.replace(hour=9, minute=0)  # Default to 9 AM
                scheduled_end = scheduled_start + timedelta(minutes=task.duration or 60)
            
            actual_duration = None
            delay = None
            
            # Calculate actual duration and delay if task was completed
            if task.actual_start_time and task.actual_end_time:
                actual_duration = int((task.actual_end_time - task.actual_start_time).total_seconds() // 60)
                delay = int((task.actual_start_time - scheduled_start).total_seconds() // 60)
            
            task_summary = TaskSummary(
                task_id=str(task.id),
                name=task.name,
                scheduled_duration=task.duration,
                actual_duration=actual_duration,
                scheduled_start_time=scheduled_start,
                scheduled_end_time=scheduled_end,
                actual_start_time=task.actual_start_time,
                actual_end_time=task.actual_end_time,
                status=task.status,
                priority=task.priority,
                delay=delay
            )
            
            task_summaries.append(task_summary)
        
        return task_summaries
    
    async def generate_ai_summary(self, metrics: ProductivityMetrics, tasks: List[TaskSummary]) -> str:
        """Generate an AI summary of the day's productivity using g4f."""
        try:
            # Prepare task data for the AI
            task_data = []
            for task in tasks:
                status_str = "completed" if task.status == "completed" else "not completed"
                delay_str = ""
                if task.delay is not None:
                    if task.delay > 0:
                        delay_str = f"started {task.delay} minutes late"
                    elif task.delay < 0:
                        delay_str = f"started {abs(task.delay)} minutes early"
                    else:
                        delay_str = "started on time"
                
                task_info = f"Task '{task.name}' (priority {task.priority}): {status_str}"
                if delay_str:
                    task_info += f", {delay_str}"
                
                task_data.append(task_info)
            
            # Skip AI generation and provide a basic summary
            # This is a workaround for the g4f module issue
            completed_count = len([t for t in tasks if t.status == "completed"])
            total_count = len(tasks)
            completion_percentage = (completed_count / total_count) * 100 if total_count > 0 else 0
            
            basic_summary = f"You completed {completed_count} out of {total_count} tasks ({completion_percentage:.1f}%). "
            
            if metrics.productivity_score > 80:
                basic_summary += "Great job! Your productivity was excellent today."
            elif metrics.productivity_score > 60:
                basic_summary += "Good work today. You maintained decent productivity."
            else:
                basic_summary += "There's room for improvement in your task completion and time management."
            
            if metrics.avg_delay > 0:
                basic_summary += f" On average, you started tasks {metrics.avg_delay:.1f} minutes late."
            
            logger.info("Generated basic summary due to AI generation issues")
            return basic_summary
            
            # The code below is commented out due to issues with the g4f library
            '''
            # Create prompt for the AI
            prompt = f"""
            Please provide a brief summary (3-5 sentences) of this productivity report:
            
            Metrics:
            - Completion rate: {metrics.completion_rate}%
            - On-time rate: {metrics.on_time_rate}%
            - Average delay: {metrics.avg_delay} minutes
            - Productivity score: {metrics.productivity_score}/100
            - Time efficiency: {metrics.time_efficiency}
            
            Tasks:
            {chr(10).join(task_data)}
            
            Focus on insights about time management, task prioritization, and suggestions for improvement.
            Be encouraging but honest about areas for improvement.
            """
            
            # Generate AI response
            response = g4f.ChatCompletion.create(
                model=self.gpt_model,
                messages=[
                    {"role": "system", "content": "You are a productivity coach analyzing daily task performance."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            logger.info("Generated AI summary successfully")
            return response
            '''
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return "Could not generate AI summary. Please try again later."
    
    async def generate_daily_report(self, tasks: List[TaskInDB], report_date: date, user_id: str) -> ReportCreate:
        """Generate a daily productivity report."""
        # Prepare task summaries
        task_summaries = self.prepare_task_summaries(tasks)
        
        # Calculate metrics
        metrics = self.calculate_metrics(task_summaries)
        
        # Generate AI summary
        ai_summary = await self.generate_ai_summary(metrics, task_summaries)
        
        # Convert date to datetime for MongoDB compatibility
        report_datetime = datetime.combine(report_date, datetime.min.time())
        
        # Create report
        report = ReportCreate(
            date=report_datetime,
            user_id=user_id,
            tasks=task_summaries,
            metrics=metrics,
            ai_summary=ai_summary
        )
        
        logger.info(f"Generated daily report for user {user_id} on {report_date}")
        return report
    
    def generate_pdf_report(self, report: ReportCreate, output_path: str) -> str:
        """Generate a PDF report from the report data."""
        try:
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title = Paragraph(f"Daily Productivity Report - {report.date}", styles["Title"])
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # Metrics section
            metrics_title = Paragraph("Productivity Metrics", styles["Heading2"])
            elements.append(metrics_title)
            elements.append(Spacer(1, 10))
            
            metrics_data = [
                ["Metric", "Value"],
                ["Completion Rate", f"{report.metrics.completion_rate}%"],
                ["On-Time Rate", f"{report.metrics.on_time_rate}%"],
                ["Average Delay", f"{report.metrics.avg_delay} minutes"],
                ["Productivity Score", f"{report.metrics.productivity_score}/100"],
                ["Time Efficiency", f"{report.metrics.time_efficiency}"]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[200, 200])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (1, 0), 12),
                ('BACKGROUND', (0, 1), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(metrics_table)
            elements.append(Spacer(1, 20))
            
            # Tasks section
            tasks_title = Paragraph("Task Summary", styles["Heading2"])
            elements.append(tasks_title)
            elements.append(Spacer(1, 10))
            
            task_data = [["Task", "Priority", "Status", "Scheduled", "Actual", "Delay"]]
            for task in report.tasks:
                scheduled_time = f"{task.scheduled_start_time.strftime('%H:%M')} - {task.scheduled_end_time.strftime('%H:%M')}"
                
                if task.actual_start_time and task.actual_end_time:
                    actual_time = f"{task.actual_start_time.strftime('%H:%M')} - {task.actual_end_time.strftime('%H:%M')}"
                else:
                    actual_time = "N/A"
                
                delay = f"{task.delay} min" if task.delay is not None else "N/A"
                
                task_data.append([
                    task.name,
                    str(task.priority),
                    task.status,
                    scheduled_time,
                    actual_time,
                    delay
                ])
            
            tasks_table = Table(task_data, colWidths=[120, 50, 70, 100, 100, 60])
            tasks_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(tasks_table)
            elements.append(Spacer(1, 20))
            
            # AI Summary
            if report.ai_summary:
                summary_title = Paragraph("AI Insights", styles["Heading2"])
                elements.append(summary_title)
                elements.append(Spacer(1, 10))
                
                summary_text = Paragraph(report.ai_summary, styles["Normal"])
                elements.append(summary_text)
            
            # Build PDF
            doc.build(elements)
            logger.info(f"Generated PDF report at {output_path}")
            
            return output_path
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            raise 