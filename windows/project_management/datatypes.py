

class Asset:
    def __init__(self, uid, org_uid):
        self.uid = uid
        self.org_uid = org_uid

    def update_in_core():
        pass

class Container:
    def __init__(self, uid, name, asset, groups_list, groups_details={}, applications=[]):
        self.uid = uid
        self.name = name
        self.asset = asset 
        self.groups_list = groups_list
        self.groups = self.parse_groups(groups_details)
        self.applications = applications

    def parse_groups(self, groups_details): # {'group_name':('group_uid', {'project_name':'project_uid'})}
        groups = []
        for group_name, group_details in groups_details.items():
            groups.append(Group(uid=group_details[0], name=group_name, container=self, projects_details=groups_details[1]))
        return groups

class Group:
    def __init__(self, uid, name, container=None, projects_details=None):
        self.uid = uid
        self.name = name
        self.container = container
        self.projects_details = projects_details



# asset_uid, org_uid = "", ""
# asset_a = Asset(asset_uid, org_uid)
# container_uid = asset_a.containers[0]
# container_a = Container(container_uid, asset_a)


# container_a.asset.org_uid

