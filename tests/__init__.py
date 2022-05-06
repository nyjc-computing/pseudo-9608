import sys



def capture(captureType):
    # Initialise a storage object to capture results
    storage = {'data': None}
    
    def captureOutput(
        *objects,
        sep=' ',
        end='\n',
        file=sys.stdout,
        flush=False,
    ):
        """
        Captures output into a storage object.
        Can be used interchangeably with Python's built-in print().
        """
        pass

    def returnData():
        """Returns the captured data"""
        return storage['data']

    if captureType == 'output':
        storage['data'] = ''
        return captureOutput, returnData
    