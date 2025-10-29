terraform {
	required_version = ">= 1.5.0"
	required_providers {
		azurerm = {
			source  = "hashicorp/azurerm"
			version = ">= 3.100.0"
		}
	}
}

provider "azurerm" {
	features {}
}

variable "resource_group_name" {
	type        = string
	description = "Name of the Azure resource group."
}

variable "location" {
	type        = string
	description = "Azure region"
	default     = "eastus"
}

variable "environment" {
	type        = string
	description = "Deployment environment (dev|staging|prod)."
	default     = "dev"
}

resource "azurerm_resource_group" "rg" {
	name     = var.resource_group_name
	location = var.location
}

resource "azurerm_log_analytics_workspace" "logs" {
	name                = "${var.resource_group_name}-logs"
	location            = azurerm_resource_group.rg.location
	resource_group_name = azurerm_resource_group.rg.name
	sku                 = "PerGB2018"
	retention_in_days   = 30
}

resource "azurerm_container_app_environment" "env" {
	name                       = "${var.resource_group_name}-cae"
	resource_group_name        = azurerm_resource_group.rg.name
	location                   = azurerm_resource_group.rg.location
	log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

resource "azurerm_container_app" "api" {
	name                         = "${var.resource_group_name}-api"
	resource_group_name          = azurerm_resource_group.rg.name
	container_app_environment_id = azurerm_container_app_environment.env.id
	revision_mode                = "Single"

	identity {
		type = "SystemAssigned"
	}

	ingress {
		external_enabled = true
		target_port      = 8000
		transport        = "auto"
	}

	template {
		container {
			name   = "smart-warehouse-api"
			image  = "${azurerm_container_registry.acr.login_server}/smart-warehouse:latest"
			cpu    = 0.5
			memory = "1Gi"

			env {
				name  = "SW_ENVIRONMENT"
				value = var.environment
			}

			env {
				name  = "SW_DATABASE__URL"
				value = "postgresql+asyncpg://warehouse:${var.postgres_password}@${azurerm_postgresql_flexible_server.database.fqdn}:5432/warehouse"
			}
		}
	}
}

resource "azurerm_container_registry" "acr" {
	name                = "${replace(var.resource_group_name, "-", "") }acr"
	resource_group_name = azurerm_resource_group.rg.name
	location            = azurerm_resource_group.rg.location
	sku                 = "Standard"
	admin_enabled       = true
}

variable "postgres_password" {
	type        = string
	description = "Administrator password for PostgreSQL flexible server."
	sensitive   = true
}

resource "azurerm_postgresql_flexible_server" "database" {
	name                   = "${var.resource_group_name}-pg"
	resource_group_name    = azurerm_resource_group.rg.name
	location               = azurerm_resource_group.rg.location
	version                = "14"
	administrator_login    = "warehouse"
	administrator_password = var.postgres_password
	sku_name               = "B_Standard_B1ms"
	storage_mb             = 32768
	zone                   = "1"

	backup {
		backup_retention_days        = 7
		geo_redundant_backup_enabled = false
	}
}

resource "azurerm_postgresql_flexible_database" "warehouse" {
	name      = "warehouse"
	server_id = azurerm_postgresql_flexible_server.database.id
	charset   = "UTF8"
	collation = "en_US.utf8"
}

output "container_app_url" {
	value = azurerm_container_app.api.latest_revision_fqdn
}
