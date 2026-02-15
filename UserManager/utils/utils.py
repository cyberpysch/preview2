def get_all_children(account):
    children = []
    direct_children = account.children.all()

    for child in direct_children:
        children.append(child)
        children.extend(get_all_children(child))

    return children
