#!/usr/bin/env node
import 'source-map-support/register'
import * as cdk from 'aws-cdk-lib'
import { SrgBackendStack } from '../lib/srg-backend-stack'

function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`Missing required environment variable: ${name}`)
  return value
}

const app = new cdk.App()

new SrgBackendStack(app, 'SrgBackendStack', {
  containerEnv: {
    STRAVA_CLIENT_ID: requireEnv('STRAVA_CLIENT_ID'),
    STRAVA_CLIENT_SECRET: requireEnv('STRAVA_CLIENT_SECRET'),
    STRAVA_REDIRECT_URI: requireEnv('STRAVA_REDIRECT_URI'),
    FRONTEND_URL: requireEnv('FRONTEND_URL'),
    DJANGO_SECRET_KEY: requireEnv('DJANGO_SECRET_KEY'),
    DB_PASSWORD: requireEnv('DB_PASSWORD'),
  },
  aws_env: {
    AWS_CLUSTER_ARN: requireEnv('AWS_CLUSTER_ARN'),
    AWS_DEFAULT_SG: requireEnv('AWS_DEFAULT_SG'),
    AWS_VPC_ID: requireEnv('AWS_VPC_ID'),
    ALB_LISTENER_ARN: requireEnv('ALB_LISTENER_ARN'),
  },
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
})
