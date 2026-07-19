# Fix a specific invoice
python manage.py fix_invoice_status --invoice INV-F1FA4527

# Fix a specific invoice with verbose output
python manage.py fix_invoice_status --invoice INV-F1FA4527 --verbose

# Check what would be changed without saving (dry run)
python manage.py fix_invoice_status --all --dry-run

# Fix all invoices
python manage.py fix_invoice_status --all

# Fix all invoices with verbose output
python manage.py fix_invoice_status --all --verbose

# Run all repair operations
python manage.py repair_invoices --all

# Only recalculate payment totals
python manage.py repair_invoices --repay

# Only update overdue status
python manage.py repair_invoices --fix-overdue

# Only clean orphaned payments
python manage.py repair_invoices --clean-payments