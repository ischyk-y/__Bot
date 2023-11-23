def get_invite_link(invite_link):
    start_index = invite_link.find('+')
    return invite_link[start_index:start_index + 9]
