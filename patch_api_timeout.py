import re

file_path = "app_motorista/lib/core/api_service.dart"
with open(file_path, "r") as f:
    content = f.read()

old_send = """      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);"""

new_send = """      final streamedResponse = await request.send().timeout(const Duration(seconds: 120));
      final response = await http.Response.fromStream(streamedResponse).timeout(const Duration(seconds: 120));"""

if old_send in content:
    content = content.replace(old_send, new_send)
    with open(file_path, "w") as f:
        f.write(content)
    print("Patched timeout.")
else:
    print("Could not find block.")
