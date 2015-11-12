##########################################################
# manage all the dynamically loaded modules of the gateway.

modules = []                                    # the list of dynamically loaded modules.

def load(moduleNames, cloud):
    """Loads all the gateway modules"""
    global modules
    modules = map(__import__, moduleNames)
    for mod in modules:
        mod.connectToGateway(cloud)

def run():
    """run the main function of each module in it's own thread"""