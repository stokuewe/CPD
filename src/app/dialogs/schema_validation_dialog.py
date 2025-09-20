"""
Dialog for handling schema validation results and user choices.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QMessageBox, QDialogButtonBox
)

from src.services.schema_validator import SchemaValidationResult


class SchemaValidationDialog(QDialog):
    """Dialog to show schema validation results and get user choice"""
    
    def __init__(self, parent, validation_result: SchemaValidationResult, project_name: str = ""):
        super().__init__(parent)
        self.validation_result = validation_result
        self.project_name = project_name
        self.user_choice = None  # 'deploy', 'proceed', 'cancel'
        
        self.setWindowTitle("Database Schema Validation")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_text = f"Schema Validation Results"
        if self.project_name:
            title_text += f" - {self.project_name}"
        
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Status message
        status_label = QLabel()
        if self.validation_result.error_message:
            status_label.setText(f"❌ Validation Error: {self.validation_result.error_message}")
            status_label.setStyleSheet("color: red; font-weight: bold;")
        elif self.validation_result.has_no_tables:
            status_label.setText("📋 Remote database has no tables - schema deployment required")
            status_label.setStyleSheet("color: orange; font-weight: bold;")
        elif self.validation_result.is_valid:
            status_label.setText("✅ Schema validation successful - database is properly configured")
            status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            status_label.setText("⚠️ Schema deviations detected - review required")
            status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        layout.addWidget(status_label)
        
        # Details text area
        details_text = self._build_details_text()
        if details_text:
            details_label = QLabel("Details:")
            details_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addWidget(details_label)
            
            details_edit = QTextEdit()
            details_edit.setPlainText(details_text)
            details_edit.setReadOnly(True)
            details_edit.setMaximumHeight(200)
            layout.addWidget(details_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if self.validation_result.error_message:
            # Error case - only allow cancel
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self._on_cancel)
            button_layout.addWidget(cancel_btn)
            
        elif self.validation_result.has_no_tables:
            # No tables - offer to deploy schema
            deploy_btn = QPushButton("Deploy Schema")
            deploy_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            deploy_btn.clicked.connect(self._on_deploy)
            button_layout.addWidget(deploy_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self._on_cancel)
            button_layout.addWidget(cancel_btn)
            
        elif self.validation_result.is_valid:
            # Valid schema - just close
            ok_btn = QPushButton("Continue")
            ok_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            ok_btn.clicked.connect(self._on_proceed)
            button_layout.addWidget(ok_btn)
            
        else:
            # Deviations - offer to proceed or cancel
            proceed_btn = QPushButton("Proceed Anyway")
            proceed_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
            proceed_btn.clicked.connect(self._on_proceed)
            button_layout.addWidget(proceed_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self._on_cancel)
            button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _build_details_text(self) -> str:
        """Build detailed text description of validation results"""
        if self.validation_result.error_message:
            return f"Error during validation:\n{self.validation_result.error_message}"
        
        if self.validation_result.has_no_tables:
            return ("The remote database contains no tables. The application requires specific tables "
                   "to function properly. Click 'Deploy Schema' to automatically create the required "
                   "database structure from azure.sql.")
        
        if self.validation_result.is_valid:
            return "All required tables are present and match the expected schema."
        
        # Build deviation details
        details = []
        
        if self.validation_result.missing_tables:
            details.append("Missing Tables:")
            for table in self.validation_result.missing_tables:
                details.append(f"  • {table}")
            details.append("")
        
        if self.validation_result.extra_tables:
            details.append("Extra Tables (not in azure.sql):")
            for table in self.validation_result.extra_tables:
                details.append(f"  • {table}")
            details.append("")
        
        if self.validation_result.table_deviations:
            details.append("Table Schema Deviations:")
            for table_name, deviations in self.validation_result.table_deviations.items():
                details.append(f"  {table_name}:")
                for deviation in deviations:
                    details.append(f"    - {deviation}")
            details.append("")
        
        if not details:
            return "No specific issues detected."
        
        details.append("Proceeding with these deviations may cause application errors or data inconsistencies.")
        
        return "\n".join(details)
    
    def _on_deploy(self):
        """User chose to deploy schema"""
        # Confirm deployment
        reply = QMessageBox.question(
            self,
            "Confirm Schema Deployment",
            "This will create tables and structures in the remote database according to azure.sql.\n\n"
            "Are you sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.user_choice = 'deploy'
            self.accept()
    
    def _on_proceed(self):
        """User chose to proceed despite issues"""
        if not self.validation_result.is_valid and not self.validation_result.has_no_tables:
            # Confirm proceeding with deviations
            reply = QMessageBox.warning(
                self,
                "Confirm Proceed",
                "The database schema has deviations from the expected structure. "
                "This may cause application errors or data inconsistencies.\n\n"
                "Are you sure you want to proceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        self.user_choice = 'proceed'
        self.accept()
    
    def _on_cancel(self):
        """User chose to cancel"""
        self.user_choice = 'cancel'
        self.reject()


class SchemaDeploymentProgressDialog(QDialog):
    """Simple progress dialog for schema deployment"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Deploying Schema")
        self.setModal(True)
        self.setFixedSize(300, 100)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Deploying database schema...")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
    
    def update_status(self, status: str):
        """Update the status message"""
        self.status_label.setText(status)
        self.repaint()  # Force immediate update
