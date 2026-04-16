"""LLM extraction service — PDF text → structured LLM output → extracted fields."""
from __future__ import annotations

import importlib
import hashlib
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from typing import Any

import os

import fitz  # PyMuPDF

from compliance_os.web.services.llm_runtime import extract_json, extract_json_with_model
from compliance_os.web.services.model_router import resolve as resolve_model

logger = logging.getLogger(__name__)


@dataclass
class TextExtractionResult:
    text: str
    engine: str
    metadata: dict[str, Any]


SCHEMAS: dict[str, dict[str, str]] = {
    "account_security_setup": {
        "platform_name": "Platform or account system shown in the setup screen",
        "setup_step": "Current setup step or screen title",
        "account_identifier": "Primary visible account identifier — prefer email if shown, otherwise username, otherwise masked ID. Return exactly one value, not multiple",
        "setup_date": "Date shown on the setup screen (YYYY-MM-DD) if visible",
    },
    "articles_of_organization": {
        "entity_name": "Legal name of the company or LLC",
        "filing_state": "State where the articles were filed",
        "filing_date": "Date the articles were filed (YYYY-MM-DD)",
        "entity_id": "State filing number or entity identification number",
        "registered_agent_name": "Name of the registered agent",
        "registered_agent_address": "Physical address of the registered agent",
        "mailing_address": "Mailing address of the company if shown",
        "principal_office_address": "Principal office address of the company if shown",
    },
    "annual_account_summary": {
        "account_holder_name": "Primary account holder name if shown",
        "institution_name": "Financial institution or broker name",
        "statement_period_start": "Statement or summary period start date (YYYY-MM-DD) if visible",
        "statement_period_end": "Statement or summary period end date (YYYY-MM-DD) if visible",
        "ending_balance": "Ending or closing balance amount (number only) if visible",
    },
    "bank_account_application": {
        "application_id": "Application or form identifier",
        "account_owner_name": "Account owner or entity name",
        "institution_name": "Institution name if visible",
        "submission_date": "Submission or application date (YYYY-MM-DD) if visible",
        "account_type": "Requested account type if visible",
    },
    "bank_account_record": {
        "institution_name": "Bank or financial institution name if visible",
        "account_holder_name": "Account holder name or entity name if visible",
        "account_number_last4": "Last four digits of the account number if visible",
        "record_date": "Date shown on the record or screenshot (YYYY-MM-DD) if visible",
    },
    "business_license": {
        "entity_name": "Registered company or business name",
        "registration_number": "Registration number or unified social credit code",
        "issuing_authority": "Issuing or registration authority if visible",
        "issue_date": "Issue or establishment date (YYYY-MM-DD) if visible",
    },
    "certificate_of_good_standing": {
        "entity_name": "Legal name of the entity",
        "jurisdiction": "Jurisdiction or state issuing the certificate",
        "entity_type": "Entity type such as Limited Liability Company",
        "formation_date": "Date the entity was formed or qualified (YYYY-MM-DD)",
        "entity_id": "State entity identification number",
        "standing_status": "Current standing status stated in the certificate",
        "duration": "Entity duration if stated, such as Perpetual",
    },
    "company_filing": {
        "entity_name": "Legal entity name referenced in the filing",
        "filing_type": "Filing type or event name",
        "jurisdiction": "Filing jurisdiction if visible",
        "filing_date": "Filing date (YYYY-MM-DD) if visible",
    },
    "chat_export_asset": {
        "archive_name": "Chat export archive folder name or bundle name if visible",
        "asset_name": "Asset filename or UI asset name",
        "asset_category": "Asset category such as image, icon, photo, or thumbnail",
    },
    "registered_agent_consent": {
        "entity_name": "Name of the business entity",
        "registered_agent_name": "Name of the registered agent",
        "registered_office_address": "Registered office physical address",
        "consent_date": "Date the consent was signed (YYYY-MM-DD)",
        "signer_name": "Printed name of the signer if present",
        "signer_title": "Title of the signer if present",
    },
    "admission_letter": {
        "student_name": "Student or applicant full name",
        "institution_name": "Institution issuing the admission letter",
        "program_name": "Program, degree, or major if visible",
        "admission_date": "Admission or offer date (YYYY-MM-DD) if visible",
    },
    "bank_statement": {
        "institution_name": "Bank or financial institution name if visible",
        "account_holder_name": "Primary account holder or entity name if visible",
        "statement_period_start": "Statement period start date (YYYY-MM-DD) if visible",
        "statement_period_end": "Statement period end date (YYYY-MM-DD) if visible",
        "ending_balance": "Ending or closing balance amount (number only) if visible",
    },
    "payment_options_notice": {
        "issuer_name": "Bank, lender, or issuer name shown on the notice",
        "account_reference_last4": "Last four digits or short account reference if visible",
        "notice_date": "Notice or statement date (YYYY-MM-DD) if visible",
        "available_payment_methods": "Short list of payment methods or channels offered",
    },
    "collection_notice": {
        "creditor_name": "Creditor, collector, or agency name if visible",
        "account_reference": "Account or correspondence reference number if visible",
        "issue_date": "Issue date or notice date (YYYY-MM-DD) if visible",
        "balance_due": "Balance due amount (number only) if visible",
    },
    "entity_notice": {
        "entity_name": "Entity or company name referenced in the notice",
        "issuer_name": "Issuing agency or sender name if visible",
        "notice_type": "Short notice type such as EIN cancellation or account notice",
        "notice_date": "Notice date (YYYY-MM-DD) if visible",
        "reference_number": "Reference number or account number if visible",
    },
    "financial_support_affidavit": {
        "student_name": "Student name if visible",
        "sponsor_name": "Sponsor or affiant name if visible",
        "support_amount": "Stated support amount (number only) if visible",
        "document_date": "Signature or issue date (YYYY-MM-DD) if visible",
        "institution_name": "School or program name if visible",
    },
    "cover_letter": {
        "candidate_name": "Candidate full name",
        "target_company": "Company or organization the letter is addressed to",
        "target_role": "Role or position referenced in the cover letter if visible",
        "letter_date": "Letter date (YYYY-MM-DD) if visible",
        "contact_email": "Candidate email address if visible",
    },
    "check_image": {
        "payor_name": "Name of the account holder or payer if visible",
        "payee_name": "Payee line or named recipient if visible",
        "check_date": "Check date (YYYY-MM-DD) if visible",
        "amount": "Check amount (number only) if visible",
        "memo": "Memo line or note if visible",
    },
    "debt_clearance_letter": {
        "issuer_name": "Issuer or collector name if visible",
        "subject_name": "Person or account holder referenced in the clearance letter",
        "clearance_date": "Debt clearance or confirmation date (YYYY-MM-DD) if visible",
        "account_reference": "Account or case reference number if visible",
    },
    "cpt_application": {
        "student_name": "Student full name",
        "institution_name": "Institution or school running the CPT or internship course",
        "course_name": "Course or CPT program name if visible",
        "approval_date": "Application or approval date (YYYY-MM-DD) if visible",
        "employer_name": "Employer or internship host if visible",
    },
    "event_invitation": {
        "event_name": "Event or conference name",
        "sender_name": "Sender or organizer name if visible",
        "recipient_name": "Recipient name or email if visible",
        "sent_date": "Invitation or email date (YYYY-MM-DD) if visible",
    },
    "enrollment_verification": {
        "student_name": "Student full name",
        "institution_name": "School or university name",
        "enrollment_status": "Enrollment status such as currently enrolled or continued attendance",
        "effective_date": "Effective or issue date (YYYY-MM-DD) if visible",
    },
    "filing_confirmation": {
        "platform_name": "Platform, portal, or service referenced in the confirmation",
        "confirmation_type": "Type of confirmation such as filing, submission, or proof of delivery",
        "confirmation_date": "Confirmation or submission date (YYYY-MM-DD) if visible",
        "reference_number": "Reference number, order number, or confirmation ID if visible",
    },
    "identifier_record": {
        "identifier_value": "Identifier, token, checksum, or opaque key value shown in the record",
        "identifier_kind": "Short guess of the identifier kind such as checksum, token, or reference",
        "source_context": "Source context suggesting what system or workflow the identifier belongs to",
    },
    "final_evaluation": {
        "student_name": "Student full name if visible",
        "employer_name": "Employer name if visible",
        "evaluation_date": "Final evaluation date (YYYY-MM-DD) if visible",
        "supervisor_name": "Supervisor or evaluator name if visible",
        "summary": "Short summary of the final evaluation if visible",
    },
    "identity_document": {
        "full_name": "Full name on the identity document if visible",
        "document_type": "Document type, such as national ID card or identification page",
        "document_number": "Document number if visible",
        "date_of_birth": "Date of birth (YYYY-MM-DD) if visible",
    },
    "immigration_reference": {
        "document_title": "Title of the guide, instructions, or reference material",
        "issuing_organization": "Issuing school, agency, or organization if visible",
        "topic": "Primary immigration topic covered by the document",
        "document_date": "Issue or update date (YYYY-MM-DD) if visible",
    },
    "insurance_card": {
        "carrier_name": "Insurance carrier or network name",
        "member_name": "Member or cardholder name",
        "member_id": "Member or policy ID",
        "group_number": "Group number if visible",
    },
    "insurance_record": {
        "carrier_name": "Insurance carrier or provider name if visible",
        "member_name": "Member or applicant name if visible",
        "record_type": "Record type such as eligibility notice or insurance document",
        "effective_date": "Coverage or issue date (YYYY-MM-DD) if visible",
    },
    "language_test_certificate": {
        "candidate_name": "Candidate or test taker full name if visible",
        "test_name": "Test name such as JLPT or IELTS",
        "test_date": "Test or score-report date (YYYY-MM-DD) if visible",
        "score_summary": "Overall level, band, or pass result if visible",
    },
    "legal_services_agreement": {
        "client_name": "Client or beneficiary name if visible",
        "provider_name": "Law firm, attorney, or service provider name if visible",
        "agreement_date": "Agreement or signature date (YYYY-MM-DD) if visible",
        "matter_type": "Matter or service scope, such as H-1B registration or immigration services",
        "signed_status": "Whether the agreement appears signed, executed, or pending signature",
    },
    "membership_welcome_packet": {
        "organization_name": "Club, association, or organization name",
        "recipient_name": "Recipient or member name if visible",
        "welcome_date": "Welcome or issue date (YYYY-MM-DD) if visible",
    },
    "school_policy_notice": {
        "institution_name": "School or program name if visible",
        "document_title": "Title of the notice or packet",
        "policy_topic": "Primary topic such as CPT, internship courses, or student introduction",
        "document_date": "Issue or publication date (YYYY-MM-DD) if visible",
    },
    "name_change_notice": {
        "subject_name": "Employer, entity, or person whose name changed",
        "prior_name": "Prior or former name if visible",
        "new_name": "New name if visible",
        "effective_date": "Effective date of the name change (YYYY-MM-DD) if visible",
    },
    "order_confirmation": {
        "merchant_name": "Merchant, vendor, or platform name if visible",
        "order_number": "Order or confirmation number if visible",
        "order_date": "Order or confirmation date (YYYY-MM-DD) if visible",
        "total_amount": "Total charged or paid amount (number only) if visible",
    },
    "profile_photo": {
        "subject_name": "Person associated with the photo if known from surrounding context",
        "asset_kind": "Photo type such as headshot, profile photo, or portrait",
        "source_context": "Folder or workflow context suggesting how the image is used",
    },
    "i983": {
        "student_name": "Full name of the student",
        "sevis_number": "SEVIS number (format: N followed by 10 digits)",
        "school_name": "Name of the school or university",
        "degree_level": "Degree level (Bachelor's, Master's, Doctoral)",
        "major": "Major field of study",
        "employer_name": "Name of the employer",
        "employer_ein": "Employer EIN (format: XX-XXXXXXX)",
        "employer_address": "Employer mailing address",
        "work_site_address": "Physical work site address",
        "job_title": "Job title / position",
        "start_date": "Employment start date (YYYY-MM-DD)",
        "end_date": "Employment end date (YYYY-MM-DD)",
        "compensation": "Annual compensation (number only)",
        "compensation_type": "Compensation type (Salary, hourly, stipend)",
        "duties_description": "Description of job duties and responsibilities",
        "training_goals": "Training goals and objectives",
        "supervisor_name": "Supervisor / mentor name",
        "supervisor_title": "Supervisor title",
        "supervisor_phone": "Supervisor phone number",
        "full_time": "Full-time employment (true/false)",
    },
    "employment_letter": {
        "employee_name": "Employee full name",
        "employer_name": "Employer / company name",
        "employer_address": "Employer address",
        "job_title": "Job title / position",
        "start_date": "Employment start date (YYYY-MM-DD)",
        "end_date": "Employment end date (YYYY-MM-DD) or null if ongoing",
        "compensation": "Annual compensation (number only)",
        "compensation_type": "Compensation type (Salary, hourly)",
        "duties_description": "Description of job duties and responsibilities",
        "manager_name": "Manager / supervisor name",
        "full_time": "Full-time or part-time (true for full-time)",
        "work_location": "Work location / office address",
    },
    "employment_screenshot": {
        "platform_name": "Platform or app shown in the screenshot",
        "participants": "Visible participants, contacts, or user names if shown",
        "screenshot_topic": "Short summary of the visible employment-related context",
        "captured_date": "Visible screenshot or message date (YYYY-MM-DD) if shown",
    },
    "non_disclosure_agreement": {
        "agreement_title": "Title of the NDA or confidentiality agreement",
        "disclosing_party": "Disclosing party name if visible",
        "receiving_party": "Receiving party name if visible",
        "effective_date": "Agreement effective date (YYYY-MM-DD) if visible",
    },
    "news_article": {
        "headline": "Article headline",
        "publisher_name": "Publisher or outlet name",
        "publication_date": "Publication date (YYYY-MM-DD) if visible",
        "subject_entity": "Primary company or organization covered by the article",
    },
    "tax_return": {
        "form_type": "Tax form type (1040, 1040-NR, 1120, 1120-S, 1065)",
        "tax_year": "Tax year (number)",
        "entity_name": "Entity name (for business returns) or null",
        "ein": "EIN (format: XX-XXXXXXX) or null",
        "filing_status": "Filing status (Single, MFJ, etc.) or null",
        "total_income": "Total income amount (number)",
        "schedules_present": "List of schedules present (e.g., schedule_c, schedule_d, schedule_nec)",
        "form_5472_present": "Whether Form 5472 is attached (true/false)",
        "form_3520_present": "Whether Form 3520 is attached (true/false)",
        "form_8938_present": "Whether Form 8938 is attached (true/false)",
        "state_returns_filed": "List of state abbreviations for state returns filed",
    },
    "1099": {
        "form_variant": "1099 variant such as 1099-INT or 1099-NEC if visible",
        "tax_year": "Tax year referenced by the form if visible (number)",
        "recipient_name": "Recipient or payee name if visible",
        "payer_name": "Payer or institution name if visible",
        "amount": "Primary amount reported on the form (number only) if visible",
    },
    "degree_certificate": {
        "student_name": "Full name of the degree holder",
        "institution_name": "Name of the issuing institution",
        "degree_awarded": "Degree or diploma awarded",
        "field_of_study": "Major or field of study if visible",
        "conferral_date": "Degree conferral date (YYYY-MM-DD) if visible",
    },
    "drivers_license": {
        "full_name": "Full legal name on the license",
        "license_number": "Driver license number",
        "date_of_birth": "Date of birth (YYYY-MM-DD)",
        "expiration_date": "License expiration date (YYYY-MM-DD)",
        "address": "Residential address if visible",
        "issuing_state": "Issuing state or jurisdiction",
    },
    "ein_application_instructions": {
        "document_title": "Instruction document title",
        "issuing_authority": "Issuing authority or platform if visible",
        "target_form": "Target filing or application referenced by the instructions",
        "last_updated_date": "Last updated date (YYYY-MM-DD) if visible",
    },
    "i20": {
        "student_name": "Full name of the student",
        "sevis_number": "SEVIS number (format: N followed by 10 digits)",
        "school_name": "Name of the school or university",
        "program": "Program name and degree level (e.g., Master's in Computer Science)",
        "major": "Major field of study",
        "program_start_date": "Program start date (YYYY-MM-DD)",
        "program_end_date": "Program end date (YYYY-MM-DD)",
        "employer_name": "CPT employer name if CPT is authorized, otherwise null",
        "work_site_address": "CPT work location/address if authorized, otherwise null",
        "start_date": "CPT employment start date (YYYY-MM-DD) if authorized, otherwise null",
        "end_date": "CPT employment end date (YYYY-MM-DD) if authorized, otherwise null",
        "full_time": "CPT full-time or part-time (true for full-time, false for part-time, null if no CPT)",
        "travel_signature_date": "Most recent DSO travel signature date (YYYY-MM-DD) if visible",
    },
    "i94": {
        "admission_number": "Admission number from the I-94 record",
        "most_recent_entry_date": "Most recent date of entry into the United States (YYYY-MM-DD)",
        "class_of_admission": "Class of admission, such as F-1 or H-1B",
        "admit_until_date": "Admit until date (YYYY-MM-DD), or D/S if that is what is shown",
        "port_of_entry": "Port of entry if visible",
    },
    "ead": {
        "card_number": "Card number on the Employment Authorization Document",
        "uscis_number": "USCIS number / A-number if visible",
        "category": "Category code shown on the card, such as C03C",
        "card_expires_on": "Card expiration date (YYYY-MM-DD)",
        "date_of_birth": "Date of birth (YYYY-MM-DD) if visible",
        "full_name": "Full name on the card",
    },
    "w2": {
        "tax_year": "Tax year for the W-2 (number)",
        "employee_name": "Employee full name",
        "employer_name": "Employer name",
        "employer_ein": "Employer EIN (format: XX-XXXXXXX)",
        "wages_tips_other_compensation": "Box 1 wages, tips, other compensation (number only)",
        "federal_income_tax_withheld": "Federal income tax withheld (number only)",
        "social_security_wages": "Social security wages (number only)",
        "state": "State abbreviation in boxes 15-20 if visible",
    },
    "ein_letter": {
        "entity_name": "Legal business name associated with the EIN",
        "ein": "Employer identification number (format: XX-XXXXXXX)",
        "assigned_date": "Date the EIN was assigned (YYYY-MM-DD) if visible",
        "business_address": "Business mailing address if visible",
    },
    "passport": {
        "full_name": "Passport holder full name",
        "passport_number": "Passport number",
        "country_of_issue": "Issuing country or authority",
        "date_of_birth": "Date of birth (YYYY-MM-DD)",
        "issue_date": "Passport issue date (YYYY-MM-DD) if visible",
        "expiration_date": "Passport expiration date (YYYY-MM-DD)",
    },
    "1042s": {
        "tax_year": "Tax year associated with the Form 1042-S (number)",
        "recipient_name": "Name of the recipient/payee",
        "recipient_address": "Recipient mailing address",
        "recipient_account_number": "Recipient account number if shown",
        "date_of_birth": "Recipient date of birth (YYYY-MM-DD) if shown",
        "income_code": "Income code shown on the form",
        "gross_income": "Gross income amount (number only)",
        "federal_tax_withheld": "Federal tax withheld amount (number only)",
        "withholding_agent_name": "Name of the withholding agent",
    },
    "lease": {
        "lease_type": "Lease type such as lease or sublease",
        "landlord_name": "Landlord, owner, or sublessor name",
        "tenant_names": "Names of the tenant or sublessee parties",
        "property_address": "Full property address including unit if visible",
        "lease_start_date": "Lease or sublease start date (YYYY-MM-DD)",
        "lease_end_date": "Lease or sublease end date (YYYY-MM-DD)",
        "monthly_rent": "Monthly rent amount (number only)",
        "security_deposit": "Security deposit amount (number only)",
    },
    "insurance_policy": {
        "carrier_name": "Insurance carrier or provider name",
        "insured_name": "Name of the insured member",
        "membership_id": "Membership, policy, or member ID",
        "policy_start_date": "Policy or coverage start date (YYYY-MM-DD)",
        "policy_end_date": "Policy end date (YYYY-MM-DD) if visible",
        "deductible": "Deductible amount (number only) if visible",
        "support_phone": "Support or claims phone number if visible",
    },
    "health_coverage_application": {
        "applicant_name": "Primary applicant full name",
        "application_date": "Application date (YYYY-MM-DD)",
        "date_of_birth": "Applicant date of birth (YYYY-MM-DD)",
        "phone_number": "Primary phone number",
        "email": "Email address",
        "street_address": "Street address",
        "city": "City",
        "state": "State abbreviation",
        "zip_code": "ZIP code",
        "county": "County if visible",
        "subsidy_requested": "Whether the applicant requested free or low cost coverage / subsidy (true/false)",
    },
    "payment_service_agreement": {
        "platform_name": "Payment platform or service provider name",
        "merchant_name": "Merchant or account holder name",
        "effective_date": "Agreement effective date (YYYY-MM-DD) if visible",
        "agreement_type": "Agreement or service type if visible",
    },
    "payment_account_record": {
        "platform_name": "Platform or payment service name",
        "account_name": "Displayed account or merchant name",
        "account_identifier": "Account identifier or merchant ID if visible",
        "record_date": "Screenshot or statement date (YYYY-MM-DD) if visible",
    },
    "payment_receipt": {
        "merchant_name": "Merchant or payee name if visible",
        "receipt_number": "Receipt or transaction number if visible",
        "payment_date": "Payment date (YYYY-MM-DD) if visible",
        "amount_paid": "Payment amount (number only) if visible",
    },
    "wire_transfer_record": {
        "sender_name": "Sender or remitter name if visible",
        "recipient_name": "Recipient or beneficiary name if visible",
        "origin_institution": "Originating bank or institution if visible",
        "destination_institution": "Destination bank or institution if visible",
        "transfer_date": "Transfer date (YYYY-MM-DD) if visible",
        "amount": "Transfer amount (number only) if visible",
        "reference_number": "Transfer reference, serial number, or transaction number if visible",
    },
    "signature_page": {
        "document_title": "Title or agreement name associated with the signature page",
        "signer_name": "Signer name if visible",
        "signature_date": "Signature date (YYYY-MM-DD) if visible",
        "signature_platform": "Signature platform or method if visible, such as DocuSign",
    },
    "public_key": {
        "key_owner": "Owner or system associated with the key if visible",
        "algorithm": "Key algorithm or format, such as RSA2",
        "key_prefix": "Beginning of the key material or identifier if visible",
    },
    "recovery_codes": {
        "provider_name": "Provider or system issuing the recovery codes",
        "account_identifier": "Primary account identifier — prefer email if shown, otherwise username, otherwise masked ID. Return exactly one value",
        "code_count": "Number of recovery codes shown if visible",
    },
    "residence_certificate": {
        "resident_name": "Resident name if visible",
        "address": "Address shown on the certificate",
        "issue_date": "Issue date (YYYY-MM-DD) if visible",
        "issuing_authority": "Issuing authority if visible",
    },
    "resume": {
        "candidate_name": "Candidate full name",
        "primary_title": "Headline, target role, or primary title if visible",
        "email": "Primary email address if visible",
        "phone_number": "Primary phone number if visible",
    },
    "work_sample": {
        "document_title": "Document title",
        "subject_area": "Subject area or topic",
        "author_name": "Author or presenter name if visible",
        "created_date": "Document or presentation date (YYYY-MM-DD) if visible",
    },
    "ein_application": {
        "legal_name": "Legal entity name shown in the EIN application",
        "organization_type": "Organization type, such as LLC",
        "filing_state": "State or territory where the entity is or will be filed",
        "start_date": "Business start date (YYYY-MM-DD)",
        "physical_address": "Physical location address",
        "phone_number": "Business phone number",
        "responsible_party_name": "Responsible party name",
    },
    "paystub": {
        "employee_name": "Employee full name",
        "employer_name": "Employer or PEO name",
        "pay_period_start": "Pay period start date (YYYY-MM-DD)",
        "pay_period_end": "Pay period end date (YYYY-MM-DD)",
        "pay_date": "Pay date or check date (YYYY-MM-DD)",
        "gross_pay": "Gross pay amount (number only)",
        "net_pay": "Net pay amount (number only)",
        "ytd_gross_pay": "Year-to-date gross pay amount if visible (number only)",
    },
    "i9": {
        "employee_name": "Employee full name",
        "employee_first_day_of_employment": "Employee's first day of employment (YYYY-MM-DD)",
        "citizenship_status": "Citizenship or immigration status selected on the form",
        "document_title": "Primary document title entered in Supplement B if visible",
        "issuing_authority": "Issuing authority for the document if visible",
        "document_number": "Document number if visible",
        "document_expiration_date": "Document expiration date (YYYY-MM-DD) if visible",
    },
    "e_verify_case": {
        "case_number": "E-Verify case number",
        "report_prepared_date": "Report prepared date (YYYY-MM-DD)",
        "company_name": "Employer or company name",
        "employee_name": "Employee full name",
        "employee_first_day_of_employment": "Employee's first day of employment (YYYY-MM-DD)",
        "citizenship_status": "Citizenship status listed in the report",
        "document_description": "Document description listed in the report",
        "case_status": "Case result or status if visible",
    },
    "i765": {
        "applicant_name": "Applicant full name",
        "eligibility_category": "Eligibility category or requested authorization category",
        "application_reason": "Reason for applying such as initial permission or renewal",
        "mailing_address": "Mailing address",
        "date_of_birth": "Applicant date of birth (YYYY-MM-DD)",
        "country_of_citizenship": "Country of citizenship or nationality",
        "a_number": "A-Number if visible",
        "uscis_online_account_number": "USCIS online account number if visible",
    },
    "h1b_registration": {
        "registration_number": "USCIS H-1B registration number",
        "employer_name": "Business or organization name",
        "employer_ein": "Employer identification number (format: XX-XXXXXXX or digits only if OCR merged it)",
        "employer_address": "Primary U.S. office or mailing address",
        "authorized_individual_name": "Authorized individual current legal name",
        "authorized_individual_title": "Authorized individual position or title at the business",
    },
    "h1b_registration_roster": {
        "company_name": "Company or petitioner name",
        "beneficiary_name": "Beneficiary full name if visible",
        "beneficiary_date_of_birth": "Beneficiary date of birth (YYYY-MM-DD) if visible",
        "export_date": "Export or roster date (YYYY-MM-DD) if visible",
    },
    "h1b_registration_worksheet": {
        "worksheet_scope": "Whether the worksheet is for the beneficiary employee or petitioning employer",
        "beneficiary_name": "Beneficiary or employee full name if visible",
        "date_of_birth": "Beneficiary date of birth (YYYY-MM-DD) if visible",
        "passport_number": "Passport number if visible",
        "current_immigration_status": "Current U.S. immigration status if visible",
        "status_expiration_date": "Current immigration-status expiration date (YYYY-MM-DD) if visible",
        "employer_name": "Petitioning employer legal name if visible",
        "employer_ein": "Employer FEIN or EIN if visible",
        "employer_address": "Primary U.S. office or mailing address if visible",
        "authorized_signatory_name": "Authorized signatory or preparer name if visible",
        "authorized_signatory_title": "Authorized signatory title if visible",
    },
    "h1b_status_summary": {
        "status_title": "Main title of the summary, such as H-1B Status",
        "registration_window_start_date": "USCIS H-1B registration opening date (YYYY-MM-DD) if stated",
        "registration_window_end_date": "USCIS H-1B registration closing date (YYYY-MM-DD) if stated",
        "petition_filing_window_start_date": "Full petition filing period start date (YYYY-MM-DD) if stated",
        "petition_filing_window_end_date": "Full petition filing period end date (YYYY-MM-DD) if stated",
        "employment_start_date": "Expected H-1B employment start date (YYYY-MM-DD) if stated",
        "law_firm_name": "Law firm or preparer organization name if visible",
    },
    "h1b_g28": {
        "representative_name": "Attorney or accredited representative full name",
        "law_firm_name": "Law firm or organization name",
        "representative_email": "Attorney or representative email address",
        "client_name": "Client full name",
        "client_entity_name": "Client entity legal name if present",
        "client_email": "Client email address if present",
    },
    "h1b_filing_invoice": {
        "invoice_number": "Invoice number or reference identifier",
        "invoice_date": "Invoice issue date (YYYY-MM-DD)",
        "petitioner_name": "Petitioning employer or entity billed",
        "beneficiary_name": "Beneficiary or employee name",
        "legal_fee_amount": "Legal fee amount (number only)",
        "uscis_fee_amount": "USCIS filing or registration fee amount (number only)",
        "total_due_amount": "Total due amount on the invoice (number only)",
        "payment_status": "Payment status if indicated, such as paid or unpaid",
    },
    "h1b_filing_fee_receipt": {
        "transaction_id": "Payment transaction identifier",
        "transaction_date": "Transaction date (YYYY-MM-DD)",
        "response_message": "Gateway response message such as APPROVAL",
        "approval_code": "Payment approval code if present",
        "cardholder_name": "Cardholder or payer name",
        "amount": "Transaction amount (number only)",
        "description": "Payment description or memo",
    },
    "operating_agreement": {
        "entity_name": "Legal entity name in the agreement",
        "entity_state": "State of formation if visible",
        "effective_date": "Agreement effective date (YYYY-MM-DD) if visible",
        "member_names": "Member or owner names if visible",
        "manager_structure": "Whether the company is member-managed or manager-managed",
    },
    "employment_contract": {
        "employee_name": "Employee full name",
        "employer_name": "Employer or company name",
        "job_title": "Job title or role",
        "effective_date": "Effective or start date (YYYY-MM-DD) if visible",
        "compensation": "Compensation amount (number only) if visible",
    },
    "employment_correspondence": {
        "sender_name": "Sender or author name if visible",
        "recipient_name": "Primary recipient name if visible",
        "organization_name": "Employer, law firm, or organization referenced in the correspondence",
        "correspondence_date": "Message or letter date (YYYY-MM-DD) if visible",
        "subject_summary": "Short summary of the issue or request discussed",
    },
    "social_security_card": {
        "full_name": "Full name on the card",
        "ssn_number": "Social Security number",
        "card_type": "Card legend or restriction if visible",
    },
    "social_security_record": {
        "holder_name": "Name of the number holder if visible",
        "birth_date": "Birth date of the holder (YYYY-MM-DD) if visible",
        "record_type": "Record type such as SSNAP printout or replacement-card request",
        "citizenship_status": "Citizenship or work-authorization status if visible",
        "mailing_address": "Mailing address shown on the record if visible",
    },
    "student_id": {
        "student_name": "Student full name",
        "institution_name": "Institution name",
        "student_id_number": "Student ID number",
        "expiration_date": "Card expiration date (YYYY-MM-DD) if visible",
    },
    "support_request": {
        "subject": "Support request subject or title",
        "request_date": "Request date (YYYY-MM-DD) if visible",
        "requester_name": "Requester name if visible",
        "organization_name": "Organization referenced in the request if visible",
    },
    "system_configuration_screenshot": {
        "platform_name": "System or settings application shown in the screenshot",
        "screen_title": "Visible screen title or settings pane name",
        "adapter_name": "Visible network adapter or interface name if shown",
        "ipv4_address": "IPv4 address if shown",
        "ipv6_address": "IPv6 address if shown",
    },
    "tax_interview": {
        "respondent_name": "Name of the person or entity completing the interview",
        "tax_residency_status": "Stated tax residency or withholding status",
        "interview_date": "Interview or submission date (YYYY-MM-DD) if visible",
        "platform_name": "Platform or vendor name if visible",
    },
    "tax_notice": {
        "agency_name": "Tax agency or authority name if visible",
        "entity_name": "Entity or taxpayer name if visible",
        "notice_type": "Type of tax notice if visible",
        "notice_date": "Notice date (YYYY-MM-DD) if visible",
        "tax_year": "Tax year if visible",
    },
    "tuition_statement": {
        "institution_name": "School or issuer name if visible",
        "student_name": "Student name if visible",
        "tax_year": "Tax year if visible",
        "qualified_tuition_amount": "Qualified tuition or payments received amount (number only) if visible",
        "statement_date": "Statement date (YYYY-MM-DD) if visible",
    },
    "transfer_pending_letter": {
        "student_name": "Student full name if visible",
        "institution_name": "Institution issuing the transfer-pending letter",
        "effective_date": "Letter date or effective date (YYYY-MM-DD) if visible",
        "status_summary": "Short summary of the pending transfer status",
    },
    "transcript": {
        "student_name": "Student full name",
        "institution_name": "Institution name",
        "degree_program": "Degree or program name if visible",
        "document_date": "Issue date or transcript date (YYYY-MM-DD) if visible",
        "credential_level": "Degree level if visible",
    },
    "visa_stamp": {
        "full_name": "Passport holder full name if visible",
        "visa_class": "Visa class such as F-1 or B1/B2",
        "issue_date": "Visa issue date (YYYY-MM-DD) if visible",
        "expiration_date": "Visa expiration date (YYYY-MM-DD) if visible",
        "issuing_post": "Issuing post or consulate if visible",
    },
    "w4": {
        "employee_name": "Employee full name",
        "tax_year": "Tax year referenced by the form if visible",
        "filing_status": "Selected filing status",
        "multiple_jobs_checkbox": "Whether the multiple jobs checkbox is selected (true/false)",
    },
    "wage_notice": {
        "employee_name": "Employee full name if visible",
        "employer_name": "Employer name if visible",
        "notice_date": "Notice or signature date (YYYY-MM-DD) if visible",
        "rate_of_pay": "Rate of pay amount (number only) if visible",
    },
}


def extract_pdf_text(file_path: str | Path) -> str:
    """Backward-compatible text-only wrapper around the richer extraction result."""
    return extract_pdf_text_with_provenance(file_path).text


def extract_pdf_text_with_provenance(file_path: str | Path) -> TextExtractionResult:
    """Extract text from a supported file type.

    Historically this function only handled PDFs, but the document-store path
    now uses it as the shared text extraction entry point for PDFs, images,
    DOCX, and plain text files.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".docx":
        from compliance_os.web.services.docx_reader import extract_docx_text

        text, metadata = extract_docx_text(file_path)
        return TextExtractionResult(text=text, engine="docx_xml", metadata=metadata)

    if suffix in {".txt", ".csv"}:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return TextExtractionResult(
            text=text,
            engine="plain_text",
            metadata={"source": "plain_text", "suffix": suffix},
        )

    # Extract text from a PDF or image file. Uses Mistral OCR if available,
    # then falls back to local PyMuPDF parsing.
    mistral_key = os.environ.get("MISTRAL_API_KEY")

    if mistral_key:
        try:
            text, metadata = _extract_with_mistral_ocr(str(file_path), mistral_key)
            return TextExtractionResult(text=text, engine="mistral_ocr", metadata=metadata)
        except Exception as exc:
            logger.warning("Mistral OCR failed for %s: %s", file_path, exc)

    # Fallback: PyMuPDF local extraction
    doc = fitz.open(str(file_path))
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    page_count = len(doc)
    doc.close()
    return TextExtractionResult(
        text="\n".join(text_parts),
        engine="pymupdf",
        metadata={"page_count": page_count, "source": "pymupdf"},
    )


def _build_mistral_client(api_key: str):
    """Create a Mistral client compatible with the installed SDK layout."""
    try:
        module = importlib.import_module("mistralai.client")
        mistral_cls = getattr(module, "Mistral")
    except (ImportError, AttributeError):
        module = importlib.import_module("mistralai")
        mistral_cls = getattr(module, "Mistral")
    return mistral_cls(api_key=api_key)


def _extract_with_mistral_ocr(file_path: str, api_key: str) -> tuple[str, dict[str, Any]]:
    """Use Mistral OCR API for high-quality document parsing."""
    import base64

    client = _build_mistral_client(api_key)

    # Read file and encode as base64 data URI
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Determine MIME type
    if file_path.lower().endswith(".pdf"):
        mime = "application/pdf"
    elif file_path.lower().endswith(".png"):
        mime = "image/png"
    elif file_path.lower().endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    else:
        mime = "application/octet-stream"

    b64 = base64.b64encode(file_bytes).decode()
    data_uri = f"data:{mime};base64,{b64}"

    # Call Mistral OCR
    if mime == "application/pdf":
        result = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": data_uri},
        )
    else:
        result = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "image_url", "image_url": data_uri},
        )

    # Extract text from all pages
    text_parts = []
    for page in result.pages:
        text_parts.append(page.markdown)

    return "\n\n".join(text_parts), {
        "page_count": len(result.pages),
        "model": "mistral-ocr-latest",
        "source": "mistral",
    }


def extract_supporting_excerpt(text: str, value: Any, window: int = 160) -> str | None:
    """Return a short excerpt around an extracted value when possible."""
    if value in (None, ""):
        return None

    needle = str(value).strip()
    if not needle:
        return None

    lower_text = text.lower()
    lower_needle = needle.lower()
    idx = lower_text.find(lower_needle)
    if idx == -1:
        return None

    start = max(0, idx - window)
    end = min(len(text), idx + len(needle) + window)
    return text[start:end].strip()


def _normalize_iso_date_value(value: Any) -> str | None:
    if value in (None, ""):
        return None

    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    month_name_match = re.search(r"\b([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\b", raw)
    if month_name_match:
        month_name_date = month_name_match.group(1)
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(month_name_date, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 8:
        try:
            return datetime.strptime(digits, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _normalize_numeric_value(value: Any, *, fixed_decimals: int | None = None) -> str | None:
    if value in (None, ""):
        return None

    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    raw = raw.strip("()")
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    normalized = match.group(0)
    if fixed_decimals is None:
        return normalized

    try:
        quantized = Decimal(normalized).quantize(Decimal(f"1.{'0' * fixed_decimals}"))
    except InvalidOperation:
        return normalized
    return f"{quantized:.{fixed_decimals}f}"


def _normalize_year_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    match = re.search(r"(20\d{2}|19\d{2})", str(value))
    if not match:
        return None
    return int(match.group(1))


def _normalize_i94_admit_until_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    compact = re.sub(r"[^A-Za-z/]", "", raw).upper()
    if compact in {"D/S", "DS"}:
        return "D/S"
    normalized_date = _normalize_iso_date_value(raw)
    if normalized_date:
        return normalized_date
    return raw


def _embedded_birthdate_from_long_id(text: str) -> str | None:
    for match in re.findall(r"\b\d{17}[0-9Xx]\b", text):
        candidate = _normalize_iso_date_value(match[6:14])
        if candidate:
            return candidate
    return None


def _extract_1042s_birthdate(text: str) -> str | None:
    label_match = re.search(r"13l Recipient'?s date of birth", text, re.IGNORECASE)
    if label_match:
        snippet = text[label_match.start():label_match.start() + 500]
        snippet = re.split(r"14a|Tax withheld by other agents", snippet, flags=re.IGNORECASE)[0]
        separated_match = re.search(r"((?:\d\s*\|\s*){8})", snippet)
        if separated_match:
            digits = re.sub(r"\D", "", separated_match.group(1))
            normalized = _normalize_iso_date_value(digits)
            if normalized:
                return normalized

    return _embedded_birthdate_from_long_id(text)


def _extract_1042s_account_number(text: str) -> str | None:
    match = re.search(
        r"13k Recipient'?s account number[^A-Z0-9]*([A-Z0-9-]{4,})",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return None


def _extract_1042s_income_code(text: str) -> str | None:
    match = re.search(r"\b1 Income code\b[^0-9]{0,20}(\d{1,2})", text, re.IGNORECASE)
    if match:
        return match.group(1).zfill(2)
    return None


def _extract_1042s_box_amount(text: str, label: str) -> str | None:
    match = re.search(
        rf"{re.escape(label)}[^0-9(]{{0,40}}\(?([0-9]+(?:\.[0-9]+)?)\)?",
        text,
        re.IGNORECASE,
    )
    if match:
        return _normalize_numeric_value(match.group(1), fixed_decimals=2)
    return None


def _normalize_1042s_result(text: str, result: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(result)

    birthdate = _extract_1042s_birthdate(text)
    if birthdate:
        normalized["date_of_birth"] = birthdate
    else:
        normalized["date_of_birth"] = _normalize_iso_date_value(normalized.get("date_of_birth"))

    account_number = _extract_1042s_account_number(text)
    if account_number:
        normalized["recipient_account_number"] = account_number

    income_code = _extract_1042s_income_code(text)
    if income_code:
        normalized["income_code"] = income_code

    gross_income = _extract_1042s_box_amount(text, "2 Gross income")
    if gross_income is not None:
        normalized["gross_income"] = gross_income
    else:
        normalized["gross_income"] = _normalize_numeric_value(
            normalized.get("gross_income"),
            fixed_decimals=2,
        )

    federal_tax_withheld = _extract_1042s_box_amount(text, "7a Federal tax withheld")
    if federal_tax_withheld is not None:
        normalized["federal_tax_withheld"] = federal_tax_withheld
    else:
        normalized["federal_tax_withheld"] = _normalize_numeric_value(
            normalized.get("federal_tax_withheld"),
            fixed_decimals=2,
        )

    tax_year = normalized.get("tax_year")
    if tax_year not in (None, ""):
        year_match = re.search(r"(20\d{2}|19\d{2})", str(tax_year))
        if year_match:
            normalized["tax_year"] = int(year_match.group(1))

    return normalized


def _normalize_h1b_identifier_candidate(value: Any) -> str | None:
    if value in (None, ""):
        return None

    candidate = re.sub(r"[^A-Za-z0-9-]", "", str(value).strip()).upper().strip("-")
    if not candidate:
        return None
    if len(candidate) < 6 or len(candidate) > 40:
        return None
    if not re.search(r"\d", candidate):
        return None
    if candidate in {"H1BR", "H-1BR"}:
        return None
    return candidate


def _extract_h1b_identifier_from_text(text: str) -> str | None:
    for label in ("Registration Number", "Beneficiary Confirmation Number", "Confirmation Number"):
        pattern = rf"{re.escape(label)}\s*:?\s*([A-Za-z0-9-]{{6,40}})"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidate = _normalize_h1b_identifier_candidate(match.group(1))
            if candidate:
                return candidate
    return None


def _extract_h1b_ein_digits(text: str) -> str | None:
    match = re.search(r"Employer\s+Id\s+Number\s*:\s*([0-9][0-9\-\s]{7,20})", text, re.IGNORECASE)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    if len(digits) != 9:
        return None
    return digits


def _normalize_h1b_ein(value: Any, text: str) -> str | None:
    digits = ""
    if value not in (None, ""):
        digits = re.sub(r"\D", "", str(value))
    if len(digits) != 9:
        text_digits = _extract_h1b_ein_digits(text)
        if text_digits:
            digits = text_digits
    if len(digits) == 9:
        return f"{digits[:2]}-{digits[2:]}"
    if value in (None, ""):
        return None
    raw = str(value).strip()
    return raw or None


def _extract_h1b_beneficiary_passport(text: str) -> str | None:
    match = re.search(r"Passport\s+Number\s*:\s*([A-Za-z0-9]{6,20})", text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def _extract_h1b_beneficiary_birthdate(text: str) -> str | None:
    match = re.search(
        r"Date\s+Of\s+Birth\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    return _normalize_iso_date_value(match.group(1))


def _extract_h1b_beneficiary_name(text: str) -> str | None:
    match = re.search(r"Beneficiaries[\s\S]{0,500}?Full\s+Name\s*:\s*([^\n\r:]{2,100})", text, re.IGNORECASE)
    if not match:
        return None
    name_tokens = re.findall(r"[A-Za-z]+", match.group(1))
    if not name_tokens:
        return None
    return " ".join(name_tokens[:8]).upper()


def _derive_h1b_registration_surrogate(text: str, result: dict[str, Any]) -> str | None:
    components: list[str] = []

    ein_digits = re.sub(r"\D", "", str(result.get("employer_ein") or ""))
    if len(ein_digits) == 9:
        components.append(f"ein:{ein_digits}")

    passport = _extract_h1b_beneficiary_passport(text)
    if passport:
        components.append(f"passport:{passport}")

    birthdate = _extract_h1b_beneficiary_birthdate(text)
    if birthdate:
        components.append(f"dob:{birthdate}")

    beneficiary_name = _extract_h1b_beneficiary_name(text)
    if beneficiary_name:
        components.append(f"name:{beneficiary_name}")

    if len(components) < 2:
        return None

    digest = hashlib.sha1("|".join(components).encode("utf-8")).hexdigest()[:12].upper()
    return f"DERIVED-H1BR-{digest}"


def _normalize_h1b_registration_result(text: str, result: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(result)
    normalized["employer_ein"] = _normalize_h1b_ein(normalized.get("employer_ein"), text)

    registration_number = _normalize_h1b_identifier_candidate(normalized.get("registration_number"))
    if not registration_number:
        registration_number = _extract_h1b_identifier_from_text(text)
    if not registration_number:
        registration_number = _derive_h1b_registration_surrogate(text, normalized)
    normalized["registration_number"] = registration_number

    return normalized


def _normalize_h1b_registration_worksheet_result(text: str, result: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_selected_fields(
        result,
        date_fields=("date_of_birth", "status_expiration_date"),
    )
    normalized["employer_ein"] = _normalize_h1b_ein(normalized.get("employer_ein"), text)

    scope = str(normalized.get("worksheet_scope") or "").strip().lower()
    if not scope:
        lowered_text = text.lower()
        if "petitioning employer" in lowered_text:
            scope = "employer"
        elif "beneficiary employee" in lowered_text:
            scope = "employee"
    normalized["worksheet_scope"] = scope or None

    passport = normalized.get("passport_number")
    if passport not in (None, ""):
        passport_text = re.sub(r"[^A-Za-z0-9]", "", str(passport)).upper()
        normalized["passport_number"] = passport_text or None

    return normalized


def _normalize_selected_fields(
    result: dict[str, Any],
    *,
    date_fields: tuple[str, ...] = (),
    numeric_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    normalized = dict(result)
    for field_name in date_fields:
        normalized[field_name] = _normalize_iso_date_value(normalized.get(field_name))
    for field_name in numeric_fields:
        normalized[field_name] = _normalize_numeric_value(
            normalized.get(field_name),
            fixed_decimals=2,
        )
    return normalized


def _normalize_result(doc_type: str, text: str, result: dict[str, Any]) -> dict[str, Any]:
    if doc_type == "1042s":
        return _normalize_1042s_result(text, result)
    if doc_type == "1099":
        normalized = _normalize_selected_fields(
            result,
            numeric_fields=("amount",),
        )
        tax_year = _normalize_year_value(normalized.get("tax_year"))
        if tax_year is not None:
            normalized["tax_year"] = tax_year
        return normalized
    if doc_type == "bank_statement":
        return _normalize_selected_fields(
            result,
            date_fields=("statement_period_start", "statement_period_end"),
            numeric_fields=("ending_balance",),
        )
    if doc_type == "account_security_setup":
        return _normalize_selected_fields(result, date_fields=("setup_date",))
    if doc_type == "collection_notice":
        return _normalize_selected_fields(
            result,
            date_fields=("issue_date",),
            numeric_fields=("balance_due",),
        )
    if doc_type == "entity_notice":
        return _normalize_selected_fields(result, date_fields=("notice_date",))
    if doc_type == "financial_support_affidavit":
        return _normalize_selected_fields(
            result,
            date_fields=("document_date",),
            numeric_fields=("support_amount",),
        )
    if doc_type == "payment_options_notice":
        return _normalize_selected_fields(result, date_fields=("notice_date",))
    if doc_type == "debt_clearance_letter":
        return _normalize_selected_fields(result, date_fields=("clearance_date",))
    if doc_type == "cover_letter":
        return _normalize_selected_fields(result, date_fields=("letter_date",))
    if doc_type == "check_image":
        return _normalize_selected_fields(
            result,
            date_fields=("check_date",),
            numeric_fields=("amount",),
        )
    if doc_type == "cpt_application":
        return _normalize_selected_fields(result, date_fields=("approval_date",))
    if doc_type == "event_invitation":
        return _normalize_selected_fields(result, date_fields=("sent_date",))
    if doc_type == "filing_confirmation":
        return _normalize_selected_fields(result, date_fields=("confirmation_date",))
    if doc_type == "final_evaluation":
        return _normalize_selected_fields(result, date_fields=("evaluation_date",))
    if doc_type == "immigration_reference":
        return _normalize_selected_fields(result, date_fields=("document_date",))
    if doc_type == "i20":
        return _normalize_selected_fields(
            result,
            date_fields=(
                "program_start_date",
                "program_end_date",
                "start_date",
                "end_date",
                "travel_signature_date",
            ),
        )
    if doc_type == "i94":
        normalized = _normalize_selected_fields(
            result,
            date_fields=("most_recent_entry_date",),
        )
        normalized["admit_until_date"] = _normalize_i94_admit_until_value(
            normalized.get("admit_until_date"),
        )
        return normalized
    if doc_type == "ead":
        return _normalize_selected_fields(
            result,
            date_fields=("card_expires_on", "date_of_birth"),
        )
    if doc_type == "passport":
        return _normalize_selected_fields(
            result,
            date_fields=("date_of_birth", "issue_date", "expiration_date"),
        )
    if doc_type == "w2":
        normalized = dict(result)
        tax_year = _normalize_year_value(normalized.get("tax_year"))
        if tax_year is not None:
            normalized["tax_year"] = tax_year
        return normalized
    if doc_type == "tax_return":
        normalized = dict(result)
        tax_year = _normalize_year_value(normalized.get("tax_year"))
        if tax_year is not None:
            normalized["tax_year"] = tax_year
        return normalized
    if doc_type == "tax_notice":
        normalized = _normalize_selected_fields(result, date_fields=("notice_date",))
        tax_year = _normalize_year_value(normalized.get("tax_year"))
        if tax_year is not None:
            normalized["tax_year"] = tax_year
        return normalized
    if doc_type == "tuition_statement":
        normalized = _normalize_selected_fields(
            result,
            date_fields=("statement_date",),
            numeric_fields=("qualified_tuition_amount",),
        )
        tax_year = _normalize_year_value(normalized.get("tax_year"))
        if tax_year is not None:
            normalized["tax_year"] = tax_year
        return normalized
    if doc_type == "language_test_certificate":
        return _normalize_selected_fields(result, date_fields=("test_date",))
    if doc_type == "legal_services_agreement":
        return _normalize_selected_fields(result, date_fields=("agreement_date",))
    if doc_type == "school_policy_notice":
        return _normalize_selected_fields(result, date_fields=("document_date",))
    if doc_type == "name_change_notice":
        return _normalize_selected_fields(result, date_fields=("effective_date",))
    if doc_type == "order_confirmation":
        return _normalize_selected_fields(
            result,
            date_fields=("order_date",),
            numeric_fields=("total_amount",),
        )
    if doc_type == "social_security_record":
        return _normalize_selected_fields(result, date_fields=("birth_date",))
    if doc_type == "employment_contract":
        return _normalize_selected_fields(
            result,
            date_fields=("effective_date",),
            numeric_fields=("compensation",),
        )
    if doc_type == "employment_correspondence":
        return _normalize_selected_fields(result, date_fields=("correspondence_date",))
    if doc_type == "employment_screenshot":
        return _normalize_selected_fields(result, date_fields=("captured_date",))
    if doc_type == "paystub":
        return _normalize_selected_fields(
            result,
            date_fields=("pay_period_start", "pay_period_end", "pay_date"),
            numeric_fields=("gross_pay", "net_pay", "ytd_gross_pay"),
        )
    if doc_type == "non_disclosure_agreement":
        return _normalize_selected_fields(result, date_fields=("effective_date",))
    if doc_type == "news_article":
        return _normalize_selected_fields(result, date_fields=("publication_date",))
    if doc_type == "payment_receipt":
        return _normalize_selected_fields(
            result,
            date_fields=("payment_date",),
            numeric_fields=("amount_paid",),
        )
    if doc_type == "wire_transfer_record":
        return _normalize_selected_fields(
            result,
            date_fields=("transfer_date",),
            numeric_fields=("amount",),
        )
    if doc_type == "signature_page":
        return _normalize_selected_fields(result, date_fields=("signature_date",))
    if doc_type == "i9":
        return _normalize_selected_fields(
            result,
            date_fields=("employee_first_day_of_employment", "document_expiration_date"),
        )
    if doc_type == "e_verify_case":
        return _normalize_selected_fields(
            result,
            date_fields=("report_prepared_date", "employee_first_day_of_employment"),
        )
    if doc_type == "h1b_registration":
        return _normalize_h1b_registration_result(text, result)
    if doc_type == "h1b_registration_roster":
        return _normalize_selected_fields(
            result,
            date_fields=("beneficiary_date_of_birth", "export_date"),
        )
    if doc_type == "h1b_registration_worksheet":
        return _normalize_h1b_registration_worksheet_result(text, result)
    if doc_type == "i765":
        return _normalize_selected_fields(result, date_fields=("date_of_birth",))
    if doc_type == "transfer_pending_letter":
        return _normalize_selected_fields(result, date_fields=("effective_date",))
    if doc_type == "transcript":
        return _normalize_selected_fields(result, date_fields=("document_date",))
    if doc_type == "visa_stamp":
        return _normalize_selected_fields(
            result,
            date_fields=("issue_date", "expiration_date"),
        )
    if doc_type == "w4":
        normalized = dict(result)
        tax_year = _normalize_year_value(normalized.get("tax_year"))
        if tax_year is not None:
            normalized["tax_year"] = tax_year
        return normalized
    if doc_type == "wage_notice":
        return _normalize_selected_fields(
            result,
            date_fields=("notice_date",),
            numeric_fields=("rate_of_pay",),
        )
    if doc_type == "h1b_status_summary":
        return _normalize_selected_fields(
            result,
            date_fields=(
                "registration_window_start_date",
                "registration_window_end_date",
                "petition_filing_window_start_date",
                "petition_filing_window_end_date",
                "employment_start_date",
            ),
        )
    if doc_type == "h1b_filing_invoice":
        return _normalize_selected_fields(
            result,
            date_fields=("invoice_date",),
            numeric_fields=("legal_fee_amount", "uscis_fee_amount", "total_due_amount"),
        )
    if doc_type == "h1b_filing_fee_receipt":
        return _normalize_selected_fields(
            result,
            date_fields=("transaction_date",),
            numeric_fields=("amount",),
        )
    return result


def extract_document(
    doc_type: str,
    text: str,
    *,
    usage_context: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Extract structured fields from document text using LLM.

    Returns dict of {field_name: {"value": ..., "confidence": ...}}
    """
    schema = SCHEMAS.get(doc_type, {})
    if not schema:
        return {}

    result = _normalize_result(doc_type, text, _call_llm(text, doc_type, schema, usage_context=usage_context))

    # Map to {field_name: {"value": ..., "confidence": ...}}
    fields: dict[str, dict[str, Any]] = {}
    for field_name in schema:
        value = result.get(field_name)
        confidence = 0.85 if value is not None else 0.0
        fields[field_name] = {"value": value, "confidence": confidence}

    return fields


def _call_llm(
    text: str,
    doc_type: str,
    schema: dict[str, str],
    *,
    usage_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call LLM to extract structured fields from document text.
    Provider selection is shared with chat via the LLM runtime configuration.
    """
    field_descriptions = "\n".join(f"- {name}: {desc}" for name, desc in schema.items())

    prompt = f"""Extract the following fields from this {doc_type} document.
Return a JSON object with these fields. Use null for any field you cannot find.

Fields to extract:
{field_descriptions}

Document text:
{text}

Return ONLY valid JSON, no explanation."""

    system = "You are a document field extractor. Return only valid JSON, no explanation or markdown."

    # Use doc-type-aware model routing if available
    routed = resolve_model(doc_type)
    if routed:
        return extract_json_with_model(
            provider=routed.provider,
            model=routed.model,
            system_prompt=system,
            user_prompt=prompt,
            temperature=0,
            max_tokens=4096,
            usage_context=usage_context,
        )

    # Fallback to global LLM_PROVIDER config
    return extract_json(
        system_prompt=system,
        user_prompt=prompt,
        temperature=0,
        max_tokens=4096,
        usage_context=usage_context,
    )
