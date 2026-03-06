import * as cdk from 'aws-cdk-lib'
import * as cr from 'aws-cdk-lib/custom-resources'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as ecs from 'aws-cdk-lib/aws-ecs'
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2'
import * as iam from 'aws-cdk-lib/aws-iam'
import { RetentionDays } from 'aws-cdk-lib/aws-logs'
import type { Construct } from 'constructs'

const PORT = 4000

interface SrgBackendStackProps extends cdk.StackProps {
  databaseName?: string
  containerEnv: {
    STRAVA_CLIENT_ID: string
    STRAVA_CLIENT_SECRET: string
    STRAVA_REDIRECT_URI: string
    FRONTEND_URL: string
    DJANGO_SECRET_KEY: string
    DB_PASSWORD: string
  }
  aws_env: {
    AWS_CLUSTER_ARN: string
    AWS_DEFAULT_SG: string
    AWS_VPC_ID: string
    AWS_SUBNET_IDS: string
    ALB_LISTENER_ARN: string
  }
}

export class SrgBackendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: SrgBackendStackProps) {
    super(scope, id, props)

    const postgresIp = cdk.Fn.importValue('PostgresInstancePrivateIp')
    const _databaseInstanceId = cdk.Fn.importValue('PostgresDatabaseInstanceId')
    const dbName = props.databaseName || 'strava_report'

    const dbEnv = {
      DB_HOST: postgresIp,
      DB_NAME: dbName,
      DB_USER: 'postgres',
      DB_PORT: '5432',
      DB_PASSWORD: props.containerEnv.DB_PASSWORD,
    }

    const vpc = ec2.Vpc.fromLookup(this, 'jh-imported-vpc', {
      vpcId: props.aws_env.AWS_VPC_ID,
    })

    const cluster = ecs.Cluster.fromClusterAttributes(this, 'jh-imported-cluster', {
      clusterName: 'jh-e1-ecs-cluster',
      clusterArn: props.aws_env.AWS_CLUSTER_ARN,
      securityGroups: [
        ec2.SecurityGroup.fromSecurityGroupId(
          this,
          'imported-default-sg',
          props.aws_env.AWS_DEFAULT_SG,
        ),
      ],
      vpc,
    })

    const taskRole = iam.Role.fromRoleName(this, 'jh-ecs-task-definition-role', 'jh-ecs-task-definition-role')
    const executionRole = iam.Role.fromRoleName(this, 'jh-ecs-task-execution-role', 'jh-ecs-task-execution-role')

    // ── Migration task ───────────────────────────────────────────────────────
    const migrationTaskDef = new ecs.FargateTaskDefinition(this, 'srg-migration-task', {
      taskRole,
      executionRole,
    })

    migrationTaskDef.addContainer('srg-migration-container', {
      image: ecs.ContainerImage.fromAsset('../'),
      command: ['sh', '-c', 'python scripts/ensure_db.py && python manage.py migrate'],
      environment: { ...dbEnv, ...props.containerEnv },
      logging: new ecs.AwsLogDriver({
        streamPrefix: 'srg-migrations',
        logRetention: RetentionDays.THREE_DAYS,
      }),
    })

    const migrationVersion = Date.now().toString()

    const runTaskParams = {
      cluster: props.aws_env.AWS_CLUSTER_ARN,
      taskDefinition: migrationTaskDef.taskDefinitionArn,
      launchType: 'FARGATE',
      networkConfiguration: {
        awsvpcConfiguration: {
          subnets: props.aws_env.AWS_SUBNET_IDS.split(','),
          securityGroups: [props.aws_env.AWS_DEFAULT_SG],
          assignPublicIp: 'ENABLED',
        },
      },
    }

    const migrationRunner = new cr.AwsCustomResource(this, 'RunDjangoMigrations', {
      onCreate: {
        service: 'ECS',
        action: 'runTask',
        parameters: runTaskParams,
        physicalResourceId: cr.PhysicalResourceId.of(`srg-migration-${migrationVersion}`),
      },
      onUpdate: {
        service: 'ECS',
        action: 'runTask',
        parameters: runTaskParams,
        physicalResourceId: cr.PhysicalResourceId.of(`srg-migration-${migrationVersion}`),
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          actions: ['ecs:RunTask'],
          resources: ['*'],
        }),
        new iam.PolicyStatement({
          actions: ['iam:PassRole'],
          resources: [taskRole.roleArn, executionRole.roleArn],
        }),
      ]),
      timeout: cdk.Duration.minutes(15),
    })

    // ── App service ──────────────────────────────────────────────────────────
    const appTaskDef = new ecs.FargateTaskDefinition(this, 'srg-backend-task', {
      taskRole,
      executionRole,
    })

    appTaskDef.addContainer('srg-backend-container', {
      image: ecs.ContainerImage.fromAsset('../'),
      command: ['python', 'manage.py', 'runserver', `0.0.0.0:${PORT}`],
      environment: { ...dbEnv, ...props.containerEnv },
      logging: new ecs.AwsLogDriver({
        streamPrefix: 'srg-backend',
        logRetention: RetentionDays.FIVE_DAYS,
      }),
      portMappings: [{ containerPort: PORT, hostPort: PORT }],
    })

    const appService = new ecs.FargateService(this, 'srg-backend-service', {
      cluster,
      taskDefinition: appTaskDef,
      assignPublicIp: true,
      desiredCount: 1,
      capacityProviderStrategies: [{ capacityProvider: 'FARGATE_SPOT', weight: 1 }],
      enableExecuteCommand: true,
    })

    // Ensure migrations complete before the service starts
    appService.node.addDependency(migrationRunner)

    // ── ALB ──────────────────────────────────────────────────────────────────
    const listener = elbv2.ApplicationListener.fromLookup(this, 'imported-listener', {
      listenerArn: props.aws_env.ALB_LISTENER_ARN,
    })

    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'srg-be-tg', {
      port: PORT,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [appService],
      vpc,
      healthCheck: {
        path: '/srg/healthcheck',
        healthyHttpCodes: '200',
        unhealthyThresholdCount: 2,
        healthyThresholdCount: 4,
        interval: cdk.Duration.seconds(30),
        port: PORT.toString(),
        timeout: cdk.Duration.seconds(10),
      },
    })

    listener.addTargetGroups('srg-listener-tg', {
      targetGroups: [targetGroup],
      priority: 30,
      conditions: [
        elbv2.ListenerCondition.hostHeaders(['srg-data.jameshrivnak.com']),
      ],
    })

    // Allow ECS to reach Postgres
    const postgresSecurityGroup = ec2.SecurityGroup.fromSecurityGroupId(
      this,
      'PostgresSecurityGroup',
      cdk.Fn.importValue('PostgresInstanceSecurityGroupId'),
    )
    const ecsSecurityGroup = appService.connections.securityGroups[0]
    postgresSecurityGroup.addIngressRule(
      ecsSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow SRG ECS tasks to connect to Postgres',
    )

    new cdk.CfnOutput(this, 'MigrationVersion', { value: migrationVersion })
  }
}
