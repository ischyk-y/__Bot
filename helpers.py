def get_invite_link(invite_link):
    print(invite_link)
    start_index = invite_link.find('+')
    print(start_index)
    print(invite_link[start_index:start_index+9])
    return invite_link[start_index:start_index + 9]
