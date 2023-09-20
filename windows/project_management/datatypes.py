

class Asset:
    def __init__(self, uid, org_uid):
        self.uid = uid
        self.org_uid = org_uid

    def update_in_core():
        pass

class Container:
    def __init__(self, uid, name, asset, applications=[]):
        self.uid = uid
        self.name = name
        self.asset = asset
        self.groups_dict = {}
        self.applications = applications


class Group:
    def __init__(self, uid, name, container_uid, containers_dict, projects_details=None):
        self.uid = uid
        self.name = name
        self.container = containers_dict.get(container_uid, None)
        self.projects_details = projects_details
        # Add group to container object
        if self.container:
            self.container.groups_dict[uid] = self


