class ResourceProvisioningException(Exception):
    """
    Resources could not be provisioned
    """
    pass
    
class ModelValidationException(Exception):
    """
    Validation before saving model returned issues
    """
    pass

class ResourceAvailabilityException(ResourceProvisioningException):
    """
    Requested resources are not *currently* available
    """
    pass

class ResourceExistenceException(ResourceAvailabilityException):
    """
    Requested resources do not exist or do not match any known resources
    """
    pass

