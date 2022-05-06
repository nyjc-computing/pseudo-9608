def capture(captureType):
    """
    Returns functions for data capture and retrieval.
    
    Arguments
    ---------
    - captureType: str
        The type of capture-return function pair to return

    Return
    ------
    capture(), return()
    """
    storage = {'data': None}
    
    def captureOutput(
        *objects,
        sep=' ',
        end='\n',
        **_,
    ):
        """
        Captures output into a storage object.
        Can be used interchangeably with Python's built-in print().
        """
        outputstr = sep.join([str(obj) for obj in objects]) + end
        storage['data'] += outputstr

    def returnData():
        """Returns the captured data"""
        return storage['data']

    if captureType == 'output':
        storage['data'] = ''
        return captureOutput, returnData
    