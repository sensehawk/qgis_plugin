

class Asset:
    def __init__(self, uid, org_uid):
        self.uid = uid
        self.org_uid = org_uid


class Container:
    def __init__(self, uid, asset):
        self.uid = uid
        self.asset = asset
        self.groups = self.get_groups()
    
    def get_groups():

        return 

class Group:
    def __init__(self, uid, container=None):
        self.uid = uid
        self.container = container

class Project:
    def __init__(self):
        pass


# asset_uid, org_uid = "", ""
# asset_a = Asset(asset_uid, org_uid)
# container_uid = asset_a.containers[0]
# container_a = Container(container_uid, asset_a)


# container_a.asset.org_uid

