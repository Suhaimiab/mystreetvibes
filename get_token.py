import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

# --- PASTE YOUR KEYS HERE ---
APP_KEY = "b7u23he21ktg4x1"
APP_SECRET = "4y2bg2nztopns56"

# Start the OAuth flow
auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET, token_access_type='offline')

authorize_url = auth_flow.start()
print("1. Go to this URL: " + authorize_url)
print("2. Click 'Allow' (you might need to log in).")
print("3. Copy the authorization code provided.")
auth_code = input("Enter the authorization code here: ").strip()

try:
    oauth_result = auth_flow.finish(auth_code)
    print("\nSUCCESS! Here is your REFRESH TOKEN (Save this!):")
    print("---------------------------------------------------")
    print(oauth_result.refresh_token)
    print("---------------------------------------------------")
except Exception as e:
    print('Error: %s' % (e,))
