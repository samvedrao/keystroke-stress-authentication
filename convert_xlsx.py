import pandas as pd

# Convert xlsx files to CSV
df_email = pd.read_excel(r'c:\Documents\KeyboardPersonality\datasets\email_userInformation.xlsx')
df_email.to_csv(r'data\email_userInformation.csv', index=False)
print("✓ email_userInformation.csv created")

df_fullname = pd.read_excel(r'c:\Documents\KeyboardPersonality\datasets\fullname_userInformation.xlsx')
df_fullname.to_csv(r'data\fullname_userInformation.csv', index=False)
print("✓ fullname_userInformation.csv created")

df_phone = pd.read_excel(r'c:\Documents\KeyboardPersonality\datasets\phone_userInformation.xlsx')
df_phone.to_csv(r'data\phone_userInformation.csv', index=False)
print("✓ phone_userInformation.csv created")

print("\nAll files converted successfully!")
