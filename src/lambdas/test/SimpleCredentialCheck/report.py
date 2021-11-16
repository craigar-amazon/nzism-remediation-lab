from lib.rdq import Profile

def accountInfo(event):
    profile = Profile()
    return {
        'accountId': profile.accountId
    }