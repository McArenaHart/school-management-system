from django.urls import path
from .views import (
    my_fees,
    invoice_detail,
    upload_pop,
    verification_queue,
    verify_proof,
    create_invoice,
)

app_name = "finance"

urlpatterns = [
    path("my-fees/", my_fees, name="my_fees"),
    path("invoice/<int:invoice_id>/", invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/upload-pop/", upload_pop, name="upload_pop"),

    # staff/admin/principal pages
    path("verify/", verification_queue, name="verification_queue"),
    path("verify/<int:proof_id>/approve/", verify_proof, name="verify_proof"),
    path("create-invoice/", create_invoice, name="create_invoice"),
]
