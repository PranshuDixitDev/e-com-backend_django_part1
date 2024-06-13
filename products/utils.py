# # products/utils.py
# import clamd
# from django.core.exceptions import ValidationError

# def scan_file_for_viruses(file):
#     cd = clamd.ClamdUnixSocket()
#     result = cd.scan_file(file.temporary_file_path())
#     if result.get(file.temporary_file_path())['virus'] is not None:
#         raise ValidationError("File is infected with a virus.")
