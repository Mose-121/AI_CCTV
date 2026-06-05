import os

source_file = 'd:/Teg-CCTV-main/UI/UI_Main.py'
output_dir = 'd:/Teg-CCTV-main/UI'

with open(source_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Common imports and header (lines 1 to 32)
header = "".join(lines[0:32])

# Define boundaries (0-indexed lines from original file)
# Note: lines list is 0-indexed, so line X is lines[X-1]
def get_lines(start, end=None):
    if end is None: return "".join(lines[start-1:])
    return "".join(lines[start-1:end-1])

segments = {
    'api_client.py': get_lines(156, 757), # APIClient, UIWebSocketClient, MJPGWebSocketPlayer
    'utils.py': get_lines(33, 156), # infer_rtsp..., build_rtsp..., _parse_video...
    'auth_dialogs.py': get_lines(757, 898) + get_lines(995, 1024) + get_lines(1024, 1121) + get_lines(1857, 1942),
    'employee_dialogs.py': get_lines(1121, 1294) + get_lines(1294, 1344) + get_lines(1344, 1660),
    'camera_dialogs.py': get_lines(1660, 1857) + get_lines(1942, 2051) + get_lines(2051, 2100) + get_lines(2416, 2444),
    'admin_dialogs.py': get_lines(898, 995) + get_lines(2100, 2196) + get_lines(2196, 2416) + get_lines(2895, 3575),
    'components.py': get_lines(2444, 2895) + get_lines(3575, 3664) + get_lines(4267, 4310),
    'main_window.py': get_lines(3664, 4267),
    'app_main.py': get_lines(4310)
}

# Now for each file, add the necessary imports to the top.
# For dialogs, they need the cross-file imports. We can just import everything from each other, but it's cleaner to just do what we need.

common_local_imports = """
from utils import *
from api_client import *
from components import *
from auth_dialogs import *
from employee_dialogs import *
from camera_dialogs import *
from admin_dialogs import *
"""

for filename, content in segments.items():
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(header)
        if filename != 'utils.py' and filename != 'api_client.py':
            f.write("from utils import *\nfrom api_client import *\n")
            if filename == 'main_window.py':
                 f.write("from components import *\nfrom auth_dialogs import *\nfrom employee_dialogs import *\nfrom camera_dialogs import *\nfrom admin_dialogs import *\n")
            if filename == 'app_main.py':
                 f.write("from main_window import *\nfrom components import *\nfrom auth_dialogs import *\nfrom admin_dialogs import *\nfrom camera_dialogs import *\nfrom employee_dialogs import *\n")
            if filename == 'admin_dialogs.py':
                 f.write("from components import YouTubeLikePlayer\n") 
                 # RecordingDialog uses YouTubeLikePlayer
                 # AdminHub uses RegisterDialog, ResetTempPasswordDialog
                 f.write("from auth_dialogs import RegisterDialog, ResetTempPasswordDialog\n")
        f.write(content)

print("Split completed successfully!")
