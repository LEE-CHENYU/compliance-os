"""Lightweight document classification using regex pattern matching."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Classification:
    doc_type: str | None
    confidence: str | None  # "high" or None
    source: str | None = None


AUTO_DOC_TYPE_VALUES = {"", "auto", "autodetect", "detect", "unknown"}


def _merge_pattern_maps(*pattern_maps: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for pattern_map in pattern_maps:
        for doc_type, patterns in pattern_map.items():
            merged.setdefault(doc_type, []).extend(patterns)
    return merged


FILENAME_PATTERNS: dict[str, list[str]] = {
    "account_security_setup": [r"treasury[_ -]?pass", r"security[_ -]?questions?"],
    "articles_of_organization": [r"articles?[_ -]?of[_ -]?organization"],
    "annual_account_summary": [r"year[_ -]?end[_ -]?summary", r"account[_ -]?summaries?"],
    "bank_account_application": [r"\btda\d{3,}\b", r"treasurydirect"],
    "bank_account_record": [r"银行账户", r"bank[_ -]?account"],
    "bank_statement": [r"bank[_ -]?document", r"bank[_ -]?statement", r"current[_ -]?view"],
    "business_license": [r"营业执照", r"business[_ -]?license"],
    "certificate_of_good_standing": [
        r"cert(?:ificate)?[_ -]?of[_ -]?good[_ -]?standing",
        r"good[_ -]?standing",
    ],
    "company_filing": [r"initial[_ -]?filing", r"entity[_ -]?filing", r"formation[_ -]?filing"],
    "collection_notice": [r"collection", r"correspondence"],
    "debt_clearance_letter": [r"debt[_ -]?clear(?:a|e)nce"],
    "degree_certificate": [r"diploma", r"degree[_ -]?certificate", r"学历认证", r"学位认证"],
    "drivers_license": [r"driver[’']?s[_ -]?license", r"drivers[_ -]?license"],
    "chat_export_asset": [
        r"back@?2x?",
        r"media_(?:call|contact|file|game|location|music|photo|shop|video|voice)",
        r"section_(?:calls|chats|contacts|frequent|other|photos|sessions|stories|web)",
    ],
    "check_image": [r"blank[_ -]?stock[_ -]?check", r"check[_ -]?payment"],
    "cpt_application": [r"(?:^|[^a-z0-9])cpt[_ -]?(?:app|application)(?:[^a-z0-9]|$)"],
    "ein_application_instructions": [
        r"ein.*instructions",
        r"individual[_ -]?request.*instructions",
    ],
    "event_invitation": [
        r"conference[_ -]?invitation",
        r"invitation.*congress",
        r"invitation[_ -]?to[_ -]?the[_ -]?project",
        r"project[_ -]?world",
        r"world[_ -]?congress",
    ],
    "admission_letter": [r"admission[_ -]?letter", r"offer[_ -]?of[_ -]?admission"],
    "enrollment_verification": [
        r"continued[_ -]?attend(?:ance|ence)",
        r"enrollment[_ -]?verification",
        r"continued[_ -]?enrollment",
    ],
    "identity_document": [r"identification[_ -]?page", r"identity[_ -]?document", r"national[_ -]?id", r"mom[_ -]?id"],
    "immigration_reference": [r"guide", r"instructions?", r"samplefilled", r"攻略"],
    "insurance_card": [r"medi[_ -]?card", r"insurance[_ -]?card"],
    "insurance_record": [r"insurance[_ -]?record"],
    "language_test_certificate": [r"jlpt", r"ielts", r"雅思", r"toefl"],
    "filing_confirmation": [
        r"retain[_ -]?the[_ -]?proof",
        r"proof[_ -]?of[_ -]?(?:filing|submission)",
        r"filing[_ -]?confirmation",
        r"confirmation[_ -]?of[_ -]?paper[_ -]?modification",
    ],
    "name_change_notice": [r"name[_ -]?change", r"name[_ -]?change[_ -]?notice"],
    "order_confirmation": [r"order[_ -]?confirmation"],
    "payment_receipt": [r"payment[_ -]?receipt"],
    "profile_photo": [r"profile[_ -]?photo", r"head[_ -]?shot"],
    "signature_page": [r"signature[_ -]?pages?"],
    "registered_agent_consent": [
        r"consent[_ -]?to[_ -]?appointment[_ -]?by[_ -]?registered[_ -]?agent",
        r"registered[_ -]?agent[_ -]?consent",
        r"filing[/_ -]?consent",
    ],
    "membership_welcome_packet": [
        r"welcome[_ -]?packet",
        r"welcome[_ -]?to[_ -]?the[_ -]?penn[_ -]?club",
        r"new[_ -]?member[_ -]?packet",
    ],
    "final_evaluation": [r"final[_ -]?evaluation"],
    "operating_agreement": [r"operating[_ -]?agreement"],
    "i983": [r"(?:^|[^a-z0-9])i-?983(?:[^a-z0-9]|$)", r"training[_ -]?plan"],
    "non_disclosure_agreement": [
        r"(?:^|[^a-z0-9])nda(?:[^a-z0-9]|$)",
        r"non[_ -]?disclosure",
        r"confidentiality[_ -]?agreement",
    ],
    "news_article": [r"morningstar", r"strategic[_ -]?investments?", r"announces"],
    "employment_contract": [
        r"employment[_ -]?contract",
        r"contract.*signed[_ -]?letter",
        r"signed[_ -]?letter.*contract",
    ],
    "employment_correspondence": [
        r"attorney[_ -]?letter",
        r"resignation[_ -]?notice",
        r"finalized.*employment",
        r"reminder.*action[_ -]?needed.*employment",
        r"floating[_ -]?holiday[_ -]?utilization",
        r"request[_ -]?for[_ -]?pto",
    ],
    "employment_letter": [
        r"employment[_ -]?letter",
        r"offer[_ -]?letter",
        r"employment[_ -]?offer",
        r"employer[_ -]?letter",
        r"stemopt[_ -]?employer[_ -]?letter",
        r"opt[_ -]?employer[_ -]?letter",
        r"vcv[_ -]?full[_ -]?time",
        r"vcv[_ -]?internship",
    ],
    "i20": [r"(?:^|[^a-z0-9])i-?20(?:[^a-z0-9]|$)"],
    "i94": [r"(?:^|[^a-z0-9])i-?94(?:[^a-z0-9]|$)"],
    "ead": [r"(?:^|[^a-z0-9])ead(?:[^a-z0-9]|$)", r"employment[_ -]?authorization"],
    "ein_letter": [r"cp[_ -]?575"],
    "ein_application": [r"\bein[_ -]?(?:individual[_ -]?request|application)\b", r"online[_ -]?application"],
    "social_security_card": [r"(?:^|[^a-z0-9])ssn(?:[^a-z0-9]|$)", r"social[_ -]?security"],
    "student_id": [r"student[_ -]?id", r"student[_ -]?identification"],
    "support_request": [
        r"requests?[_ -]?for[_ -]?employment[_ -]?and[_ -]?immigration[_ -]?support",
        r"support[_ -]?request",
        r"compliance[_ -]?with[_ -]?stem[_ -]?opt[_ -]?requirements",
        r"guidance[_ -]?on[_ -]?stem[_ -]?opt[_ -]?compliance",
    ],
    "social_security_record": [
        r"ssnap",
        r"replacement[_ -]?social[_ -]?security[_ -]?number[_ -]?card",
    ],
    "system_configuration_screenshot": [
        r"network[_ -]?config",
        r"ipv4",
        r"ipv6",
        r"netbios",
        r"realtek",
    ],
    "tax_interview": [r"tax[_ -]?interview"],
    "transcript": [r"transcript", r"ecertification", r"etran(?:script|scription)", r"\u6210\u7ee9\u5355"],
    "visa_stamp": [r"(?:^|[^a-z0-9])visa(?:[^a-z0-9]|$)", r"visa[_ -]?stamp"],
    "payment_account_record": [r"支付宝平台账户", r"payment[_ -]?account", r"alipay.*account"],
    "payment_service_agreement": [r"支付服务合同", r"payment[_ -]?service[_ -]?agreement"],
    "public_key": [r"alipaypublickey", r"public[_ -]?key", r"publickey", r"rsa2"],
    "recovery_codes": [r"recovery[_ -]?codes?", r"backup[_ -]?codes?", r"backup[_ -]?code"],
    "residence_certificate": [r"居住证明", r"residence[_ -]?certificate", r"proof[_ -]?of[_ -]?residence"],
    "resume": [r"resume", r"简历", r"履歴書"],
    "transfer_pending_letter": [r"transfer[_ -]?pending"],
    "wage_notice": [r"wage[_ -]?theft[_ -]?prevention[_ -]?act[_ -]?notice", r"wage[_ -]?notice"],
    "work_sample": [r"stock[_ -]?pitch", r"technicals?", r"work[_ -]?sample"],
    "w2": [r"(?:^|[^a-z0-9])w-?2(?:[^a-z0-9]|$)"],
    "w4": [r"(?:^|[^a-z0-9])w-?4(?:[^a-z0-9]|$)"],
    "passport": [r"(?:^|[^a-z0-9])passport(?:[^a-z0-9]|$)"],
    "1042s": [r"(?:^|[^a-z0-9])1042-?s(?:[^a-z0-9]|$)"],
    "tax_return": [r"tax[_ -]?return", r"(?:^|[^a-z0-9])1040(?:-nr)?(?:[^a-z0-9]|$)", r"(?:^|[^a-z0-9])1120(?:-s)?(?:[^a-z0-9]|$)", r"(?:^|[^a-z0-9])1065(?:[^a-z0-9]|$)"],
    "1099": [r"(?:^|[^a-z0-9])1099(?:[^a-z0-9]|$)"],
    "lease": [r"(?:^|[^a-z0-9])sublease(?:[^a-z0-9]|$)", r"(?:^|[^a-z0-9])lease(?:[^a-z0-9]|$)"],
    "insurance_policy": [r"nomad[_ -]?insurance", r"(?:^|[^a-z0-9])insurance(?:[^a-z0-9]|$)"],
    "health_coverage_application": [r"coveredca", r"marketplace"],
    "paystub": [r"(?:^|[^a-z0-9])pay[_ -]?stub(?:[^a-z0-9]|$)", r"paystubs?"],
    "i9": [r"(?:^|[^a-z0-9])i[_ -]?9(?:[^a-z0-9]|$)"],
    "e_verify_case": [r"e[_ -]?verify", r"everify"],
    "i765": [r"(?:^|[^a-z0-9])i[_ -]?765(?:[^a-z0-9]|$)"],
    "h1b_registration": [r"h[_ -]?1b[_ -]?r", r"h[_ -]?1b[_ -]?registration", r"uscis[_ -]?h[_ -]?1b[_ -]?registration"],
    "h1b_status_summary": [r"h[_ -]?1b[_ -]?status[_ -]?overview", r"h[_ -]?1b[_ -]?status[_ -]?summary"],
    "h1b_g28": [r"(?:^|[^a-z0-9])g[_ -]?28(?:[^a-z0-9]|$)"],
    "h1b_filing_invoice": [r"invoice[_ -]?part[_ -]?i"],
    "h1b_filing_fee_receipt": [r"transaction[_ -]?#?\d{5,}"],
    "employment_screenshot": [
        r"screenshot[_ -]?from[_ -]?justwork",
        r"whatsapp[_ -]?image",
    ],
}

PATH_CONTEXT_PATTERNS: dict[str, list[str]] = {
    "account_security_setup": [
        r"/treasury pass\.png$",
    ],
    "bank_statement": [r"/(?:tax|w2)/\d{0,4}/?bank_document_", r"/w2/bank_document_"],
    "resume": [r"/cv & cover letters/cv\d{6}/(?:chenyu|cheney|李宸宇)[^/]*\.pdf$"],
    "chat_export_asset": [
        r"/employment/bitsync/chatexport_2024-12-14(?: \(\d+\))?/(?:images|photos)/[^/]+\.(?:png|jpe?g)$",
    ],
    "company_filing": [
        r"/veeup\.cc/网站备案\.png$",
        r"/授权书/\d+_\.pic\.jpg$",
    ],
    "employment_screenshot": [
        r"/employment/rai/screenshot from justwork\.png$",
        r"/employment/[^/]+/whatsapp image \d{4}-\d{2}-\d{2} at [0-9. apm]+\.(?:jpe?g|png)$",
        r"/happyhunting screenshot/\d+_\.pic\.jpg$",
        r"/employment/bitsync/(?:will communications/)?img_\d+\.png$",
    ],
    "final_evaluation": [
        r"/stem opt/i983/.*/final evaluation opt\.pdf$",
    ],
    "health_coverage_application": [r"/medical/marketplace"],
    "immigration_reference": [
        r"/stem opt/i983/instructions/",
        r"/stem opt/stem opt申请完整攻略",
    ],
    "insurance_record": [r"/medical/n\d+_template"],
    "identity_document": [
        r"/mom id/",
    ],
    "i20": [
        r"/i20/cu[_ -]?(?:original|opt|stemopt[_ -]?23(?:_signed)?|travel[_ -]?22|travel[_ -]?23)\.pdf$",
        r"/i20/i20/\d+[^/]*\.pic\.png$",
        r"/i20/i20/i-20 travel\.rtfd/[^/]+\.(?:png|jpe?g)$",
    ],
    "admission_letter": [r"/i20/i20/admission[_ -]?letter\.pdf$"],
    "enrollment_verification": [r"/i20/(?:ciam|westcliff).*continued[_ -]?attend(?:ance|ence)\.pdf$"],
    "transfer_pending_letter": [r"/i20/(?:ciam|westcliff).*transfer[_ -]?pending\.pdf$"],
    "lease": [r"/lease/[^/]+_\d+\.pdf$"],
    "1099": [r"/tax/\d{4}/document\.pdf$"],
    "non_disclosure_agreement": [
        r"/employment/rai/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.pdf$",
    ],
    "news_article": [r"/employment/rai/.*morningstar\.pdf$"],
    "profile_photo": [
        r"/cv & cover letters/cv\d{6}/(?:img_\d+|r\d+(?: \(\d+\))?)\.jpe?g$",
    ],
    "signature_page": [
        r"/employment/vcv/signature pages\.pdf$",
        r"/stem opt/i983/.*/signature pages\.pdf$",
    ],
}


# Keep unavoidable corpus-specific legacy archive scans isolated from reusable path-context rules.
PATH_EXCEPTION_PATTERNS: dict[str, list[str]] = {
    "account_security_setup": [r"/スクリーンショット 2025-04-17 午前11\.49\.19\.png$"],
    "bank_account_record": [r"/新春竹_对公账户\.pic\.jpg$"],
    "check_image": [r"/employment/wolff & li/blank_stock_check_payment\.pdf$"],
    "company_filing": [
        r"/veeup\.cc/wechatimg14\.jpg$",
        r"/veeup\.cc/wechatimg371\.jpg$",
    ],
    "degree_certificate": [
        r"/cv & cover letters/transcript&diploma/20210713112836-0001\.pdf$",
        r"/cv & cover letters/transcript&diploma/img_0514\.jpe?g$",
    ],
    "drivers_license": [r"/personal info archive/img_1725\.pdf$"],
    "ein_application": [r"/yangtze capital/yangtze capital\.pdf$"],
    "employment_letter": [r"/stem opt/tiger cloud, llc - new york\. ny\.pdf$"],
    "final_evaluation": [r"/employment/claudius/12 month \(page-5\) \.pdf$"],
    "identity_document": [
        r"/bsgc/docs/img_(1708|2070|2227)\.jpe?g$",
        r"/personal info archive/wechatimg(?:219|220)\.jpe?g$",
        r"/img_372[12] medium\.jpe?g$",
        r"/wechatimg(?:219|220)\.jpe?g$",
    ],
    "passport": [r"/bsgc/docs/img_(0991|1709)\.jpe?g$"],
    "profile_photo": [
        r"/092e233d-f2e5-\.jpg$",
        r"/photo\.jpg$",
    ],
    "social_security_card": [r"/bsgc/docs/img_1792\.jpg$"],
    "social_security_record": [r"/personal info archive/img_1675\.pdf$"],
    "system_configuration_screenshot": [
        r"/weixin image_2025-07-02_213642_922\.png$",
        r"/veeup\.cc/wechatimg13\.jpg$",
    ],
}


PATH_PATTERNS: dict[str, list[str]] = _merge_pattern_maps(PATH_CONTEXT_PATTERNS, PATH_EXCEPTION_PATTERNS)


PATTERNS: dict[str, list[str]] = {
    "account_security_setup": [
        r"TreasuryDirect",
        r"Answer Three Security Questions",
        r"Security Questions",
    ],
    "articles_of_organization": [
        r"Articles of Organization",
        r"Limited Liability Company Articles of Organization",
        r"The name of the limited liability company is",
    ],
    "annual_account_summary": [
        r"Year[- ]?End Summary",
        r"Account Summaries",
        r"Account Summary",
    ],
    "bank_account_application": [
        r"TDA\s*\d{3,}",
        r"TreasuryDirect",
        r"entity account",
    ],
    "bank_account_record": [
        r"银行账户",
        r"Bank Account",
        r"Account Name",
        r"Account Number",
    ],
    "bank_statement": [
        r"Statement",
        r"Account Activity",
        r"Beginning Balance",
        r"Ending Balance",
    ],
    "business_license": [
        r"营业执照",
        r"Business License",
        r"Unified Social Credit Code",
        r"Registration Authority",
    ],
    "certificate_of_good_standing": [
        r"good standing",
        r"Secretary of State",
        r"entity identification number",
    ],
    "company_filing": [
        r"Initial Filing",
        r"entity filing",
        r"Secretary of State",
        r"filing",
    ],
    "collection_notice": [
        r"Collection",
        r"Correspondence",
        r"Balance Due",
    ],
    "debt_clearance_letter": [
        r"Debt Clearance",
        r"Debt Clearence",
        r"Clearance",
    ],
    "cpt_application": [
        r"Experiential Internship Courses",
        r"CPT authorization",
        r"International students will receive CPT authorization",
    ],
    "degree_certificate": [
        r"Diploma",
        r"degree of",
        r"has conferred upon",
        r"awarded the degree",
        r"学历认证",
        r"学位认证",
    ],
    "chat_export_asset": [
        r"media_call",
        r"media_contact",
        r"section_chats",
    ],
    "check_image": [
        r"Pay to the Order of",
        r"Memo",
        r"Check Number",
    ],
    "drivers_license": [
        r"DRIVER'?S LICENSE",
        r"DLN",
        r"CLASS",
        r"\bISS\b",
        r"\bEXP\b",
    ],
    "ein_application_instructions": [
        r"EIN Individual Request",
        r"Instructions",
        r"Online EIN application",
    ],
    "admission_letter": [
        r"Admission Letter",
        r"offered admission",
        r"pleased to offer admission",
    ],
    "enrollment_verification": [
        r"continued attendance",
        r"continued attendence",
        r"enrollment verification",
        r"currently enrolled",
    ],
    "filing_confirmation": [
        r"retain the proof",
        r"proof of (?:filing|submission)",
        r"(?:filing|submission) confirmation",
        r"Confirmation of paper modification",
    ],
    "identity_document": [
        r"Identification",
        r"ID Number",
        r"Date of Birth",
        r"Name",
    ],
    "immigration_reference": [
        r"Guide",
        r"Instructions",
        r"Sample",
        r"STEM OPT",
    ],
    "insurance_card": [
        r"Member ID",
        r"Insurance Card",
        r"RxBIN",
        r"RxPCN",
    ],
    "insurance_record": [
        r"Eligibility Determination",
        r"coverage",
        r"member",
        r"plan",
    ],
    "registered_agent_consent": [
        r"Consent to Appointment by Registered Agent",
        r"registered agent",
        r"voluntarily consent to serve",
    ],
    "membership_welcome_packet": [
        r"Welcome",
        r"membership",
        r"member packet",
        r"club",
    ],
    "final_evaluation": [
        r"Final Evaluation",
        r"12[- ]?Month",
        r"Evaluation on Student Progress",
    ],
    "operating_agreement": [
        r"Operating Agreement",
        r"Limited Liability Company Agreement",
        r"member[- ]managed",
        r"manager[- ]managed",
    ],
    "i983": [
        r"TRAINING PLAN FOR STEM OPT STUDENTS",
        r"Form I-983",
        r"STEM Optional Practical Training",
    ],
    "non_disclosure_agreement": [
        r"Non[- ]Disclosure",
        r"Confidential(?:ity| Information)",
        r"Receiving Party",
        r"Disclosing Party",
    ],
    "news_article": [
        r"Morningstar",
        r"Strategic Investments",
        r"XR and AI Innovation",
    ],
    "i20": [
        r"Certificate of Eligibility for Nonimmigrant Student Status",
        r"Form I-20",
        r"1-20,\s*Certificate of Eligibility",
    ],
    "i94": [
        r"Arrival\s*/\s*Departure\s*Record",
        r"Most Recent I-94",
        r"Class of Admission",
        r"Admit Until Date",
    ],
    "ead": [
        r"Employment Authorization Document",
        r"CARD EXPIRES",
        r"USCIS#",
    ],
    "passport": [r"\bPASSPORT\b", r"PASSEPORT", r"Nationality", r"P<[A-Z]{3}"],
    "ein_letter": [r"Employer Identification Number", r"EIN.*assigned", r"CP\s*575"],
    "ein_application": [
        r"receive your EIN",
        r"Summary of your information",
        r"Organization Type:\s*LLC",
    ],
    "event_invitation": [
        r"Invitation to the project",
        r"World Congress in Computer Science",
        r"Meteor Support",
    ],
    "identifier_record": [
        r"^\s*[a-f0-9]{32,64}\s*$",
    ],
    "social_security_card": [
        r"Social Security",
        r"name shown on card",
        r"This number has been established",
    ],
    "student_id": [
        r"Student ID",
        r"Student Identification",
        r"University ID",
    ],
    "support_request": [
        r"Employment and Immigration Support",
        r"support request",
        r"request for guidance",
        r"urgent matter regarding my employment",
        r"documentation requirements under the STEM OPT program",
        r"Guidance on STEM OPT Compliance and Unpaid Salary",
    ],
    "tax_interview": [
        r"Tax Interview",
        r"tax residency",
        r"substantial presence",
    ],
    "transcript": [
        r"Official Transcript",
        r"Academic Transcript",
        r"eTranscript",
        r"eCertification",
        r"\u6210\u7ee9\u5355",
    ],
    "visa_stamp": [
        r"Visa",
        r"Issuing Post",
        r"Entries",
        r"Visa Type",
    ],
    "payment_account_record": [
        r"支付宝",
        r"account",
        r"merchant",
    ],
    "payment_service_agreement": [
        r"支付服务合同",
        r"service agreement",
        r"Alipay",
    ],
    "payment_receipt": [
        r"Payment Receipt",
        r"Receipt Number",
        r"Amount Paid",
        r"Payment Date",
    ],
    "social_security_record": [
        r"SSNAP Printout",
        r"Replacement Social Security Number Card",
        r"Number Holder Name",
    ],
    "system_configuration_screenshot": [
        r"IPv4",
        r"IPv6",
        r"NetBIOS",
        r"Realtek",
    ],
    "public_key": [
        r"BEGIN PUBLIC KEY",
        r"PUBLIC KEY",
        r"RSA2",
    ],
    "recovery_codes": [
        r"backup code",
        r"backup codes",
        r"recovery code",
        r"recovery codes",
    ],
    "residence_certificate": [
        r"居住证明",
        r"Residence",
        r"Address",
    ],
    "resume": [
        r"Resume",
        r"Experience",
        r"Education",
        r"Skills",
    ],
    "language_test_certificate": [
        r"JLPT",
        r"Japanese Language Proficiency",
        r"IELTS",
        r"雅思",
    ],
    "name_change_notice": [
        r"name change",
        r"changed to",
        r"formerly known as",
    ],
    "order_confirmation": [
        r"Order Confirmation",
        r"Confirmation",
        r"Order Number",
    ],
    "transfer_pending_letter": [
        r"transfer pending",
        r"pending transfer",
        r"transfer request",
    ],
    "wage_notice": [
        r"Wage Theft Prevention Act",
        r"Notice",
        r"Rate of Pay",
    ],
    "work_sample": [
        r"Stock Pitch",
        r"Technical",
        r"Case Study",
        r"Project",
    ],
    "w2": [r"Wage and Tax Statement", r"Form W-2"],
    "w4": [r"Employee'?s Withholding Certificate", r"Form W-4"],
    "1042s": [
        r"Form 1042-S",
        r"withholding agent",
        r"federal tax withheld",
        r"recipient's account number",
    ],
    "tax_return": [
        r"Nonresident Alien Income Tax Return",
        r"U\.S\. Individual Income Tax Return",
        r"Form 1040(?!-NR)\b",
        r"Form 1040-NR",
        r"Form 1120-S",
        r"Form 1120\b",
        r"Form 1065",
    ],
    "1099": [r"Form 1099", r"Miscellaneous Income"],
    "employment_letter": [
        r"Employment Offer Letter",
        r"Offer Letter",
        r"pleased to offer you",
        r"pleased to offer you the position of",
        r"employment at will",
        r"OPT Employer letter",
        r"This is to certify that .* is employed",
        r"employment authorization in accordance with the OPT regulations",
    ],
    "lease": [
        r"Sublease Agreement",
        r"\bThis lease\b",
        r"Tenant and Owner",
        r"Premises:",
        r"Rental Agreement",
        r"Monthly Rent",
        r"Security Deposit",
    ],
    "insurance_policy": [
        r"Nomad Insurance",
        r"Membership ID",
        r"not a guarantee of coverage",
    ],
    "health_coverage_application": [
        r"CoveredCA\.com",
        r"Application date",
        r"Primary Contact for your household",
    ],
    "paystub": [
        r"Pay Period Start",
        r"Pay Period End",
        r"Pay Date",
        r"Net Pay",
    ],
    "i9": [
        r"Employment Eligibility Verification",
        r"Form I-9",
        r"U\.S\. Citizenship and Immigration Services",
    ],
    "e_verify_case": [
        r"E-Verify Case Number",
        r"Company Information",
        r"Employee Information",
        r"Case Result",
    ],
    "i765": [
        r"Application For Employment Authorization",
        r"Form I-765",
        r"USCIS Form I-765",
    ],
    "h1b_registration": [
        r"USCIS H-1B Registration",
        r"Registration Number",
        r"What is your business or organization name\?",
    ],
    "h1b_status_summary": [
        r"H[- ]?1B Status",
        r"Requirements for H[- ]?1B visa status",
        r"How to File for New H[- ]?1B visa status",
        r"Required Documents for Filing for H[- ]?1B visa status",
        r"H-1B\s*\u7533\u8bf7\u624b\u518c",
        r"\u5982\u4f55\u7533\u8bf7\u65b0\u7684\s*H-1B\s*\u7b7e\u8bc1",
    ],
    "h1b_g28": [
        r"Notice of Entry of Appearance as Attorney or Accredited Representative",
        r"DHS Form G-28",
        r"Part 3:\s*Notice of Appearance",
    ],
    "h1b_filing_invoice": [
        r"\bINVOICE\b",
        r"H[- ]?1B Cap Petition",
        r"H[- ]?1B Registration Filing Fee",
    ],
    "h1b_filing_fee_receipt": [
        r"Transaction Information",
        r"Response Message",
        r"Approval Code",
        r"H1B registration",
    ],
    "signature_page": [
        r"Signature Page",
        r"Sign Here",
        r"DocuSign",
    ],
    "employment_contract": [
        r"Employment Contract",
        r"at will employment",
        r"confidentiality",
        r"non-solicitation",
        r"employment documents",
        r"review and e-sign your employment documents",
        r"Ahead of your start date",
    ],
    "employment_correspondence": [
        r"response to your demand for unpaid wages",
        r"withdraws the offer letter",
        r"decided to resign from my position",
        r"return of company property",
        r"all parties have finalized the document",
        r"sent you .* to review and complete",
        r"Floating Holiday Utilization",
    ],
    "employment_screenshot": [
        r"Justworks",
        r"WhatsApp",
        r"Will Communications",
    ],
}


TEXT_MIN_MATCHES: dict[str, int] = {
    "account_security_setup": 2,
    "articles_of_organization": 2,
    "annual_account_summary": 2,
    "bank_account_application": 2,
    "bank_account_record": 2,
    "bank_statement": 2,
    "business_license": 2,
    "certificate_of_good_standing": 2,
    "collection_notice": 2,
    "company_filing": 2,
    "debt_clearance_letter": 2,
    "cpt_application": 2,
    "degree_certificate": 2,
    "drivers_license": 2,
    "chat_export_asset": 1,
    "check_image": 2,
    "ein_application_instructions": 2,
    "admission_letter": 2,
    "enrollment_verification": 2,
    "filing_confirmation": 2,
    "final_evaluation": 2,
    "identifier_record": 1,
    "identity_document": 2,
    "immigration_reference": 2,
    "insurance_card": 2,
    "insurance_record": 2,
    "language_test_certificate": 2,
    "name_change_notice": 2,
    "order_confirmation": 2,
    "registered_agent_consent": 2,
    "membership_welcome_packet": 2,
    "operating_agreement": 2,
    "i983": 2,
    "non_disclosure_agreement": 2,
    "news_article": 2,
    "employment_contract": 2,
    "employment_correspondence": 2,
    "employment_letter": 2,
    "i20": 2,
    "i94": 2,
    "ead": 2,
    "social_security_card": 2,
    "student_id": 2,
    "support_request": 2,
    "tax_interview": 2,
    "transcript": 2,
    "visa_stamp": 2,
    "payment_account_record": 2,
    "payment_service_agreement": 2,
    "payment_receipt": 2,
    "signature_page": 2,
    "public_key": 2,
    "recovery_codes": 2,
    "residence_certificate": 2,
    "resume": 2,
    "transfer_pending_letter": 2,
    "wage_notice": 2,
    "work_sample": 2,
    "passport": 2,
    "ein_letter": 2,
    "ein_application": 2,
    "w2": 2,
    "w4": 2,
    "1042s": 2,
    "tax_return": 2,
    "1099": 2,
    "lease": 2,
    "insurance_policy": 2,
    "health_coverage_application": 2,
    "paystub": 2,
    "i9": 2,
    "e_verify_case": 2,
    "i765": 2,
    "h1b_registration": 2,
    "h1b_status_summary": 2,
    "h1b_g28": 2,
    "h1b_filing_invoice": 2,
    "h1b_filing_fee_receipt": 2,
    "employment_screenshot": 1,
}

OCR_TEXT_MIN_MATCH_OVERRIDES: dict[str, int] = {
    # OCR on unsupported forms can mention these identifiers incidentally.
    # Raise the bar only for OCR fallback to avoid false-positive intake routing.
    "i94": 3,
    "passport": 3,
    "ein_letter": 3,
}

OCR_REQUIRED_ANY_PATTERNS: dict[str, list[str]] = {
    # Require a strong anchor for high-risk OCR classifications.
    "i94": [r"Arrival\s*/\s*Departure\s*Record"],
    "ein_letter": [r"CP\s*575"],
}


DOC_TYPE_ALIASES: dict[str, str] = {
    "1042_s": "1042s",
    "1042s": "1042s",
    "account_security_setup": "account_security_setup",
    "articles_of_organization": "articles_of_organization",
    "annual_account_summary": "annual_account_summary",
    "bank_account_application": "bank_account_application",
    "bank_account_record": "bank_account_record",
    "business_license": "business_license",
    "chat_export_asset": "chat_export_asset",
    "check_image": "check_image",
    "certificate_of_good_standing": "certificate_of_good_standing",
    "company_filing": "company_filing",
    "cpt_application": "cpt_application",
    "cp_575": "ein_letter",
    "degree_certificate": "degree_certificate",
    "diploma": "degree_certificate",
    "drivers_license": "drivers_license",
    "driver_s_license": "drivers_license",
    "ead": "ead",
    "ein_application": "ein_application",
    "ein_application_instructions": "ein_application_instructions",
    "ein_letter": "ein_letter",
    "employment_agreement": "employment_contract",
    "employment_contract": "employment_contract",
    "employment_correspondence": "employment_correspondence",
    "employment_letter": "employment_letter",
    "employment_offer": "employment_letter",
    "employment_offer_letter": "employment_letter",
    "admission_letter": "admission_letter",
    "enrollment_verification": "enrollment_verification",
    "filing_confirmation": "filing_confirmation",
    "identifier_record": "identifier_record",
    "good_standing_certificate": "certificate_of_good_standing",
    "health_coverage_application": "health_coverage_application",
    "identity_document": "identity_document",
    "immigration_guide": "immigration_reference",
    "immigration_reference": "immigration_reference",
    "i20": "i20",
    "i_20": "i20",
    "i94": "i94",
    "i_94": "i94",
    "i983": "i983",
    "i_983": "i983",
    "insurance_policy": "insurance_policy",
    "insurance_card": "insurance_card",
    "insurance_record": "insurance_record",
    "i9": "i9",
    "i_9": "i9",
    "i765": "i765",
    "i_765": "i765",
    "lease": "lease",
    "offer_letter": "employment_letter",
    "passport": "passport",
    "paystub": "paystub",
    "pay_stub": "paystub",
    "payment_account_record": "payment_account_record",
    "payment_service_agreement": "payment_service_agreement",
    "public_key": "public_key",
    "recovery_codes": "recovery_codes",
    "residence_certificate": "residence_certificate",
    "resume": "resume",
    "social_security_card": "social_security_card",
    "ssn": "social_security_card",
    "student_id": "student_id",
    "support_request": "support_request",
    "tax_interview": "tax_interview",
    "transcript": "transcript",
    "membership_welcome_packet": "membership_welcome_packet",
    "name_change_notice": "name_change_notice",
    "news_article": "news_article",
    "non_disclosure_agreement": "non_disclosure_agreement",
    "order_confirmation": "order_confirmation",
    "registered_agent_consent": "registered_agent_consent",
    "signature_page": "signature_page",
    "operating_agreement": "operating_agreement",
    "bank_statement": "bank_statement",
    "collection_notice": "collection_notice",
    "debt_clearance_letter": "debt_clearance_letter",
    "final_evaluation": "final_evaluation",
    "language_test_certificate": "language_test_certificate",
    "payment_receipt": "payment_receipt",
    "transfer_pending_letter": "transfer_pending_letter",
    "wage_notice": "wage_notice",
    "work_sample": "work_sample",
    "tax_return": "tax_return",
    "e_verify": "e_verify_case",
    "e_verify_case": "e_verify_case",
    "everify": "e_verify_case",
    "visa": "visa_stamp",
    "visa_stamp": "visa_stamp",
    "h1b_registration": "h1b_registration",
    "h_1b_registration": "h1b_registration",
    "h1b_status_summary": "h1b_status_summary",
    "h_1b_status_summary": "h1b_status_summary",
    "h1b_status_overview": "h1b_status_summary",
    "h_1b_status_overview": "h1b_status_summary",
    "h1b_g28": "h1b_g28",
    "h_1b_g28": "h1b_g28",
    "g28": "h1b_g28",
    "g_28": "h1b_g28",
    "h1b_filing_invoice": "h1b_filing_invoice",
    "h_1b_filing_invoice": "h1b_filing_invoice",
    "h1b_invoice": "h1b_filing_invoice",
    "h_1b_invoice": "h1b_filing_invoice",
    "h1b_filing_fee_receipt": "h1b_filing_fee_receipt",
    "h_1b_filing_fee_receipt": "h1b_filing_fee_receipt",
    "h1b_fee_receipt": "h1b_filing_fee_receipt",
    "h_1b_fee_receipt": "h1b_filing_fee_receipt",
    "h1b_receipt": "h1b_filing_fee_receipt",
    "h_1b_receipt": "h1b_filing_fee_receipt",
    "employment_screenshot": "employment_screenshot",
    "1099": "1099",
    "w2": "w2",
    "w4": "w4",
    "w_2": "w2",
}

SUPPORTED_DOC_TYPES = set(FILENAME_PATTERNS) | set(PATTERNS) | set(PATH_PATTERNS)


def classifier_generality_report() -> dict[str, object]:
    exception_doc_types = sorted(PATH_EXCEPTION_PATTERNS)
    context_doc_types = sorted(PATH_CONTEXT_PATTERNS)
    exception_pattern_count = sum(len(patterns) for patterns in PATH_EXCEPTION_PATTERNS.values())
    return {
        "path_context_doc_types": context_doc_types,
        "path_exception_doc_types": exception_doc_types,
        "path_context_pattern_count": sum(len(patterns) for patterns in PATH_CONTEXT_PATTERNS.values()),
        "path_exception_pattern_count": exception_pattern_count,
        "exception_only_doc_types": sorted(
            doc_type
            for doc_type in PATH_EXCEPTION_PATTERNS
            if doc_type not in PATH_CONTEXT_PATTERNS
        ),
    }


def is_auto_doc_type(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in AUTO_DOC_TYPE_VALUES


def normalize_doc_type(value: str | None) -> str | None:
    if value is None:
        return None

    raw = value.strip()
    if not raw or is_auto_doc_type(raw):
        return None

    key = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    alias = DOC_TYPE_ALIASES.get(key, key)
    return alias if alias in SUPPORTED_DOC_TYPES else None


def _pattern_scores(text: str, pattern_map: dict[str, list[str]]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for doc_type, patterns in pattern_map.items():
        score = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
        if score:
            scores[doc_type] = score
    return scores


def _best_scored_match(
    text: str,
    pattern_map: dict[str, list[str]],
    *,
    min_matches: dict[str, int] | None = None,
    required_any_patterns: dict[str, list[str]] | None = None,
    source: str | None = None,
) -> Classification:
    scores = _pattern_scores(text, pattern_map)
    if not scores:
        return Classification(doc_type=None, confidence=None)

    best_score = max(scores.values())
    winners = [doc_type for doc_type, score in scores.items() if score == best_score]
    if len(winners) != 1:
        return Classification(doc_type=None, confidence=None)

    best_doc_type = winners[0]
    required_matches = (min_matches or {}).get(best_doc_type, 1)
    if best_score < required_matches:
        return Classification(doc_type=None, confidence=None)
    required_patterns = (required_any_patterns or {}).get(best_doc_type)
    if required_patterns and not any(re.search(pattern, text, re.IGNORECASE) for pattern in required_patterns):
        return Classification(doc_type=None, confidence=None)
    return Classification(doc_type=best_doc_type, confidence="high", source=source)


def classify_text(
    text: str,
    *,
    min_matches: dict[str, int] | None = None,
    required_any_patterns: dict[str, list[str]] | None = None,
) -> Classification:
    """Classify document based on extracted text content.

    Text classification is conservative on purpose. Unsupported documents often
    mention identifiers like I-94, passport, or EIN as references, so a single
    incidental match should not drive a classification decision.
    """
    effective_min_matches = dict(TEXT_MIN_MATCHES)
    if min_matches:
        effective_min_matches.update(min_matches)
    return _best_scored_match(
        text,
        PATTERNS,
        min_matches=effective_min_matches,
        required_any_patterns=required_any_patterns,
        source="text",
    )


def classify_filename(file_path: str) -> Classification:
    """Classify a document using only its filename."""
    path = Path(file_path)
    filename = path.name.lower()
    by_name = _best_scored_match(filename, FILENAME_PATTERNS, source="filename")
    if by_name.doc_type:
        return by_name

    path_text = "/" + "/".join(part.lower() for part in path.parts)
    by_path = _best_scored_match(path_text, PATH_PATTERNS, source="filename")
    if by_path.doc_type:
        return by_path

    stem = path.stem.lower()
    generic_prefixes = ("img", "image", "photo", "scan", "document", "wechatimg", "weixin image")
    generic_stem = stem.startswith(generic_prefixes) or stem.isdigit() or stem in {"consent"}
    if generic_stem and path.parent.name:
        contextual_name = f"{path.parent.name.lower()}/{filename}"
        by_parent = _best_scored_match(contextual_name, FILENAME_PATTERNS, source="filename")
        if by_parent.doc_type:
            return by_parent

    return Classification(doc_type=None, confidence=None)


def classify_file(file_path: str, mime_type: str, *, allow_ocr: bool = True) -> Classification:
    """Classify a file by filename, local text extraction, then optional OCR fallback."""
    by_name = classify_filename(file_path)
    if by_name.doc_type:
        return by_name

    if mime_type == "application/pdf":
        from compliance_os.web.services.pdf_reader import extract_first_page

        text = extract_first_page(file_path)
        if text:
            by_text = classify_text(text)
            if by_text.doc_type:
                return by_text

    if mime_type in {"text/plain", "text/csv"}:
        try:
            text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        if text:
            by_text = classify_text(text)
            if by_text.doc_type:
                return by_text

    if allow_ocr and mime_type in {"application/pdf", "image/png", "image/jpeg"}:
        from compliance_os.web.services.extractor import extract_pdf_text

        text = extract_pdf_text(file_path)
        if text:
            by_ocr = classify_text(
                text,
                min_matches=OCR_TEXT_MIN_MATCH_OVERRIDES,
                required_any_patterns=OCR_REQUIRED_ANY_PATTERNS,
            )
            if by_ocr.doc_type:
                by_ocr.source = "ocr"
                return by_ocr

    return Classification(doc_type=None, confidence=None)
