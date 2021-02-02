from gateway.models.bacnet import ObjProperty


# FIXME
def get_fault_obj_properties(reliability: int or str,
                             pv='null',
                             sf: list = None) -> dict:
    """ Returns properties for unknown objects
    """
    if sf is None:
        sf = [0, 1, 0, 0]
    return {
        ObjProperty.presentValue: pv,
        ObjProperty.statusFlags: sf,
        ObjProperty.reliability: reliability
        #  todo: make reliability class as Enum
    }
