

class Asset:
    def __init__(self, asset_dict, org_uid):
        self.uid = asset_dict["uid"]
        self.org_uid = org_uid
        self.name = asset_dict["name"]
        self.profile_image = asset_dict["profile_image"]

    def update_in_core():
        pass

class Container:
    def __init__(self, uid, name, asset, applications=[]):
        self.uid = uid
        self.name = name
        self.asset = asset
        self.groups_dict = {}
        self.group_info = []
        self.applications = applications


class Group:
    def __init__(self, uid, name, container_uid, containers_dict, org_info, deal_id, projects_details={}):
        self.uid = uid
        self.name = name
        self.org_info = org_info
        self.container = containers_dict.get(container_uid, None)
        self.projects_details = projects_details
        self.deal_id = deal_id
        # Add group to container object
        if self.container:
            self.container.groups_dict[uid] = self
            self.container.group_info.append({'uid':uid, 'name':self.name})

