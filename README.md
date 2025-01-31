# 007 AI Financial Advisor

## What is this?
A financial advisor application with sample data provided on mock customer stock/ETF holdings and transactions. This repository provides the techniques to index complex raw data and tables for sub-second queries, create data enrichment pipelines for advanced metrics and see the power of open-source LLMs including Granite 3.0, Mixtral, and Falcon (downloaded from Hugging Face).

Create this all in one AI platform leveraging watsonx platform tools (watsonx Orchestrate, watsonx.ai), ElasticSearch, business automation from open-source projects (custom pdf-generator)/ IBM under the hood technology (App Connect Enterprise, Robotic Process Automation etc.) and connect to external data sources (Gmail email send, Yahoo Finance API, Hugging Face Falcon model)

## How to start?
Go to the tax-loss-harvesting-optimization-main branch and dive into the data, open API files, PDF generator app, prompt templates and python notes.


# IBM Client Engineering Solutions Documentation Template

## What is this?
This is a template used to quickly and effectively document assets and solutions created by Client Engineers at IBM. The template outlines the bare minimum requirements that must be documented when publishing your work.

## Install Quarto
To be able to build and view changes locally for these docs you will need to install the appropriate version of Quarto via Command Line: 
`pip install quarto-cli` or `brew install --cask quarto` and ensure one of the tools below is installed:
* VS Code
* Jupyter
* RStudio
* Neovim
* Text Editor

If the command line install does not work, you can download quarto here: https://quarto.org/docs/download/

## How do I use it?
1. Change line 9 of the `_quarto.yml` file to the appropriate Project Name of the solution doc.
2. Change line 21 of the `_quarto.yml` file to the reflect the link to the repo of the newly created solution doc. Ex. https://github.com/ibm-client-engineering/[repo-name]
3. Assuming that Quarto is already installed, navigate to the appropriate directory with the cloned solution doc repository and run `quarto preview index.qmd` to preview your build locally.