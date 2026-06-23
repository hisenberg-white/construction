"""Build the Nepali (ne) translation catalog into .po and compiled .mo.

This avoids a system gettext (msgfmt) dependency — it writes the binary .mo
directly. Run it after editing CATALOG:

    venv\\Scripts\\python.exe tools\\build_messages.py

Output: locale/ne/LC_MESSAGES/django.{po,mo}
"""
import array
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, '..', 'locale', 'ne', 'LC_MESSAGES')

HEADER = (
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Language: ne\n"
    "Plural-Forms: nplurals=2; plural=(n != 1);\n"
)

# English msgid -> Nepali msgstr. blocktrans entries keep %(var)s placeholders.
CATALOG = {
    # Top bar / nav
    "SaaS Owner": "SaaS स्वामी",
    "Language": "भाषा",
    "Logout": "लगआउट",
    "Dashboard": "ड्यासबोर्ड",
    "Masters": "मास्टर डेटा",
    "Customers": "ग्राहकहरू",
    "Suppliers": "आपूर्तिकर्ताहरू",
    "Materials": "सामग्रीहरू",
    "Services": "सेवाहरू",
    "Vehicle Types": "सवारी प्रकार",
    "Vehicles": "सवारी साधनहरू",
    "Capacity Rules": "क्षमता नियमहरू",
    "Operations": "सञ्चालन",
    "Purchases": "खरिद",
    "Trips / Splits": "ट्रिप / विभाजन",
    "Sales Invoices": "बिक्री बिलहरू",
    "Payments": "भुक्तानीहरू",
    "Ledger": "खाता",
    "Stock Ledger": "स्टक खाता",
    "Expenses": "खर्चहरू",
    "Expense Categories": "खर्च वर्गहरू",
    "Employees": "कर्मचारीहरू",
    "Work Logs": "कार्य अभिलेख",
    "Administration": "प्रशासन",
    "Depots": "डिपोहरू",
    "Company Settings": "कम्पनी सेटिङ",
    "Email Settings": "इमेल सेटिङ",
    "Users & Roles": "प्रयोगकर्ता र भूमिका",
    "Audit Log": "अडिट लग",
    "Client Companies": "ग्राहक कम्पनीहरू",
    "Plans": "योजनाहरू",
    "Subscriptions": "सदस्यताहरू",
    "Usage": "उपयोग",
    "System": "प्रणाली",
    "Django Admin": "Django एडमिन",
    # Quick-add modal / common
    "Add": "थप्नुहोस्",
    "Name": "नाम",
    "Phone": "फोन",
    "Cancel": "रद्द गर्नुहोस्",
    "Save & select": "सुरक्षित गरी छान्नुहोस्",
    # List / form / detail chrome
    "New": "नयाँ",
    "Actions": "कार्यहरू",
    "View": "हेर्नुहोस्",
    "Edit": "सम्पादन",
    "Delete": "मेटाउनुहोस्",
    "No records yet.": "अहिलेसम्म कुनै रेकर्ड छैन।",
    "Previous": "अघिल्लो",
    "Next": "अर्को",
    "Page %(n)s of %(total)s": "पृष्ठ %(n)s / %(total)s",
    "Fields marked": "चिन्ह लगाइएका फिल्ड",
    "are required.": "अनिवार्य छन्।",
    "Save": "सुरक्षित गर्नुहोस्",
    "Back": "पछाडि",
    "Yes, delete": "हो, मेटाउनुहोस्",
    "Reason": "कारण",
    "Confirm cancellation": "रद्द पुष्टि गर्नुहोस्",
    "Are you sure you want to permanently delete <strong>%(obj)s</strong>? This cannot be undone.":
        "के तपाईं <strong>%(obj)s</strong> लाई स्थायी रूपमा मेटाउन निश्चित हुनुहुन्छ? यो उल्टाउन सकिँदैन।",
    "Financial records are not deleted — cancelling <strong>%(obj)s</strong> voids it and keeps an audit trail.":
        "वित्तीय रेकर्ड मेटिँदैन — <strong>%(obj)s</strong> रद्द गर्दा यो खारेज हुन्छ र अडिट ट्रेल राख्छ।",
    # Dashboard
    "SaaS overview": "SaaS सिंहावलोकन",
    "Use the sidebar to manage master data and record daily operations.":
        "मास्टर डेटा व्यवस्थापन र दैनिक कारोबार अभिलेख गर्न साइडबार प्रयोग गर्नुहोस्।",
    "Today's Sales": "आजको बिक्री",
    "Today's Collection": "आजको संकलन",
    "Credit Due": "बाँकी उधारो",
    "Stock Value": "स्टक मूल्य",
    "Net Profit (est.)": "खुद नाफा (अनुमानित)",
    # Login / no-tenant
    "Sign in": "साइन इन",
    "Invalid username or password.": "अमान्य प्रयोगकर्ता नाम वा पासवर्ड।",
    "Username": "प्रयोगकर्ता नाम",
    "Password": "पासवर्ड",
    "No company linked": "कुनै कम्पनी जोडिएको छैन",
    "No company linked to your account": "तपाईंको खातामा कुनै कम्पनी जोडिएको छैन",
    "Your user is not yet assigned to a company. Please ask your administrator to create your profile, or sign in as a SaaS owner.":
        "तपाईंको प्रयोगकर्ता अझै कुनै कम्पनीमा तोकिएको छैन। कृपया प्रशासकलाई तपाईंको प्रोफाइल बनाउन भन्नुहोस्, वा SaaS स्वामीको रूपमा साइन इन गर्नुहोस्।",
    "Sign out": "साइन आउट",
    # Invoice screens
    "Share invoice:": "बिल साझा गर्नुहोस्:",
    "Download PDF": "PDF डाउनलोड",
    "Customer has no email": "ग्राहकको इमेल छैन",
    "Email to customer": "ग्राहकलाई इमेल",
    "Customer has no email on file.": "ग्राहकको इमेल अभिलेखमा छैन।",
    "Line Items": "लाइन वस्तुहरू",
    "Item": "वस्तु",
    "Vehicle": "सवारी",
    "Qty": "परिमाण",
    "Unit": "एकाइ",
    "Rate": "दर",
    "Amount": "रकम",
    "No line items.": "कुनै लाइन वस्तु छैन।",
    "Delivery / Share Log": "डेलिभरी / साझा लग",
    "Log delivery": "डेलिभरी लग गर्नुहोस्",
    "Not shared yet.": "अहिलेसम्म साझा गरिएको छैन।",
    "Sale Invoice": "बिक्री बिल",
    "Material": "सामग्री",
    "Service": "सेवा",
    "Vehicle Type": "सवारी प्रकार",
    "Description": "विवरण",
    "Remove": "हटाउनुहोस्",
    "Save Invoice": "बिल सुरक्षित गर्नुहोस्",
}


def _escape(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def write_po(path):
    lines = ['msgid ""', 'msgstr ""']
    for ln in HEADER.rstrip('\n').split('\n'):
        lines.append(f'"{_escape(ln)}\\n"')
    lines.append('')
    for msgid, msgstr in CATALOG.items():
        lines.append(f'msgid "{_escape(msgid)}"')
        lines.append(f'msgstr "{_escape(msgstr)}"')
        lines.append('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def write_mo(path):
    items = {'': HEADER}
    items.update(CATALOG)
    keys = sorted(items.keys())
    offsets, ids, strs = [], b'', b''
    for key in keys:
        kb = key.encode('utf-8')
        vb = items[key].encode('utf-8')
        offsets.append((len(ids), len(kb), len(strs), len(vb)))
        ids += kb + b'\x00'
        strs += vb + b'\x00'
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)
    koffsets, voffsets = [], []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    output = struct.pack('Iiiiiii', 0x950412de, 0, len(keys),
                         7 * 4, 7 * 4 + len(keys) * 8, 0, 0)
    output += array.array('i', koffsets + voffsets).tobytes()
    output += ids + strs
    with open(path, 'wb') as f:
        f.write(output)


def main():
    out = os.path.normpath(OUT_DIR)
    os.makedirs(out, exist_ok=True)
    write_po(os.path.join(out, 'django.po'))
    write_mo(os.path.join(out, 'django.mo'))
    print(f'Wrote {len(CATALOG)} translations to {out}')


if __name__ == '__main__':
    main()
