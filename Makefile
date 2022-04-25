SHELL := /bin/bash
-include .env
export $(shell sed 's/=.*//' .env)
.ONESHELL: # Applies to every targets in the file!
.PHONY: help

primary := '\033[1;36m'
bold := '\033[1m'
clear := '\033[0m'

help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help

setup:
	pip install -e .
	pip install -r -U requirements-dev.txt
	pre-commit install --hook-type pre-push --hook-type pre-commit
	detect-secrets scan > .secrets.baseline

prep: ## Cleanup tmp files
	@find . -type f -name '*.pyc' -delete 2>/dev/null
	@find . -type d -name '__pycache__' -delete 2>/dev/null
	@find . -type f -name '*.DS_Store' -delete 2>/dev/null
	@rm -f **/*.zip **/*.tar **/*.tgz **/*.gz

output:
	@echo -e $(bold)$(primary)trivialscan_arn$(clear) = $(shell terraform output trivialscan_arn)
	@echo -e $(bold)$(primary)function_url$(clear) = $(shell terraform output function_url)
	@echo -e $(bold)$(primary)trivialscan_role$(clear) = $(shell terraform output trivialscan_role)
	@echo -e $(bold)$(primary)trivialscan_role_arn$(clear) = $(shell terraform output trivialscan_role_arn)
	@echo -e $(bold)$(primary)trivialscan_policy_arn$(clear) = $(shell terraform output trivialscan_policy_arn)
	@echo -e $(bold)$(primary)rapidapi_token$(clear) = $(shell terraform output rapidapi_token)
	@echo -e $(bold)$(primary)parameter_name$(clear) = $(shell terraform output rapidapi_token_parameter_name)

build: prep ## makes the lambda zip archive
	./.$(BUILD_ENV)/bin/build-archive

tfinstall:
	curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
	sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(shell lsb_release -cs) main"
	sudo apt-get update
	sudo apt-get install -y terraform
	terraform -install-autocomplete || true

init:  ## Runs tf init tf
	terraform init -reconfigure -upgrade=true

deploy: plan apply

plan: init ## Runs tf validate and tf plan
	terraform validate
	terraform plan -no-color -out=.tfplan
	terraform show --json .tfplan | jq -r '([.resource_changes[]?.change.actions?]|flatten)|{"create":(map(select(.=="create"))|length),"update":(map(select(.=="update"))|length),"delete":(map(select(.=="delete"))|length)}' > tfplan.json

apply: ## tf apply -auto-approve -refresh=true
	terraform apply -auto-approve -refresh=true .tfplan

destroy: init ## tf destroy -auto-approve
	terraform validate
	terraform plan -destroy -no-color -out=.tfdestroy
	terraform show --json .tfdestroy | jq -r '([.resource_changes[]?.change.actions?]|flatten)|{"create":(map(select(.=="create"))|length),"update":(map(select(.=="update"))|length),"delete":(map(select(.=="delete"))|length)}' > tfdestroy.json
	terraform apply -auto-approve -destroy .tfdestroy
