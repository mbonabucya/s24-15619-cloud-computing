# 1. Specify the version of the AzureRM Provider to use
terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
      version = "=3.39.0"
    }
  }
}

# 2. Configure the AzureRM Provider
provider "azurerm" {
  features {}
}

# 3. Create an Azure Front Door resource

resource "azurerm_frontdoor" "frontdoor" {
  name                = var.frontdoor_name
  resource_group_name = var.resource_group_name

  # frontend endpoint for the Front Door instance
  frontend_endpoint {
    name      = "frontendEndpoint"
    host_name = "${var.frontdoor_name}.azurefd.net"
  }

  # health probe for the login service
  backend_pool_health_probe {
    name = "probelogin"
    # TODO: add more configurations
  }

  # health probe for the chat service
  backend_pool_health_probe {
    name = "probechat"
    # TODO: add more configurations
  }

  # load balancing settings 
  backend_pool_load_balancing {
    name = "wecloudloadbalancer"
    # TODO: add more configurations
  }

  # backend pool for the login and profile services
  backend_pool {
    name = "wecloudbackendloginprofile"

    # backend from gcp 
    backend {
      host_header = var.gcp_ingress_external_ip
      address     = var.gcp_ingress_external_ip
      # TODO: add more configurations
    }

    # backend from azure
    backend {
      host_header = var.azure_ingress_external_ip
      address     = var.azure_ingress_external_ip
      # TODO: add more configurations
    }

    # TODO: add more configurations
  }

  # backend pool for the chat service
  backend_pool {
    name = "wecloudbackendchat"

    # backend from gcp
    backend {
      host_header = var.gcp_ingress_external_ip
      address     = var.gcp_ingress_external_ip
      # TODO: add more configurations
    }

    # TODO: add more configurations
  }

  # routing rule for login and profile services
  routing_rule {
    name               = "loginprofilerouting"
    # TODO: add more configurations
  }

  # routing rule for chat service
  routing_rule {
    name               = "chatrouting"
    # TODO: add more configurations
  }
  
}