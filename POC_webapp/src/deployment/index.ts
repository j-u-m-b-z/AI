import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as awsx from "@pulumi/awsx";
import * as path from "path";
import * as fs from "fs/promises";

// Enhanced Configuration Management
interface DeploymentConfig {
  projectName: string;
  environment: string;
  region: string;
  apiEndpoint: string;
  logRetentionDays: number;
}

class WebappInfrastructure {
  // Explicitly declare properties with non-null assertion
  private websiteBucket!: aws.s3.Bucket;
  private cdn!: aws.cloudfront.Distribution;
  private errorLoggingBucket!: aws.s3.Bucket;
  private config: DeploymentConfig;

  constructor() {
    const pulumiConfig = new pulumi.Config();
    
    this.config = {
      projectName: pulumiConfig.get("projectName") || "human-image-validation-webapp",
      environment: pulumiConfig.get("environment") || "production",
      region: pulumiConfig.get("region") || "us-east-1",
      apiEndpoint: pulumiConfig.get("apiEndpoint") || "",
      logRetentionDays: parseInt(pulumiConfig.get("logRetentionDays") || "30")
    };

    // Initialize resources in the constructor
    this.createErrorLoggingBucket();
    this.createWebsiteBucket();
    this.createCloudFrontDistribution();
  }

  // Create Error Logging Bucket
  private createErrorLoggingBucket(): void {
    this.errorLoggingBucket = new aws.s3.Bucket(`${this.config.projectName}-error-logs`, {
      bucket: `${this.config.projectName}-error-logs-${this.config.environment}`,
      acl: "private",
      forceDestroy: true,
      lifecycleRules: [{
        enabled: true,
        expiration: {
          days: this.config.logRetentionDays
        }
      }]
    });
  }

  // Create Website Bucket
  private createWebsiteBucket(): void {
    this.websiteBucket = new aws.s3.Bucket(`${this.config.projectName}-website-bucket`, {
      bucket: `${this.config.projectName}-${this.config.environment}`,
      acl: "private",
      website: {
        indexDocument: "index.html",
        errorDocument: "error.html"
      },
      serverSideEncryptionConfiguration: {
        rule: {
          applyServerSideEncryptionByDefault: {
            sseAlgorithm: "AES256"
          }
        }
      },
      loggings: [{
        targetBucket: this.errorLoggingBucket.id,
        targetPrefix: "s3-access-logs/"
      }],
      forceDestroy: true
    });
  }

  // Create CloudFront Distribution
  private createCloudFrontDistribution(): void {
    this.cdn = new aws.cloudfront.Distribution(`${this.config.projectName}-cdn`, {
      enabled: true,
      origins: [{
        originId: this.websiteBucket.id,
        domainName: this.websiteBucket.websiteEndpoint,
        customOriginConfig: {
          httpPort: 80,
          httpsPort: 443,
          originProtocolPolicy: "http-only",
          originSslProtocols: ["TLSv1.2"]
        }
      }],
      defaultRootObject: "index.html",
      defaultCacheBehavior: {
        targetOriginId: this.websiteBucket.id,
        viewerProtocolPolicy: "redirect-to-https",
        allowedMethods: ["GET", "HEAD", "OPTIONS"],
        cachedMethods: ["GET", "HEAD"],
        forwardedValues: {
          queryString: false,
          cookies: { forward: "none" }
        },
        minTtl: 0,
        defaultTtl: 3600,
        maxTtl: 86400
      },
      priceClass: "PriceClass_100",
      restrictions: {
        geoRestriction: {
          restrictionType: "none"
        }
      },
      viewerCertificate: {
        cloudfrontDefaultCertificate: true
      }
    });
  }

  // Deploy Website Files
  private async deployWebsiteFiles(): Promise<void> {
    const websiteDir = path.join(__dirname, "../app/dist/human-image-validation-webapp");
    
    try {
      const files = await fs.readdir(websiteDir);
      
      files.forEach(async (file) => {
        const filePath = path.join(websiteDir, file);
        
        new aws.s3.BucketObject(`webapp-${file}`, {
          bucket: this.websiteBucket.id,
          source: new pulumi.asset.FileAsset(filePath),
          contentType: this.getContentType(file)
        });
      });
    } catch (error) {
      console.error("Website deployment error:", error);
      throw error;
    }
  }

  // Determine Content Type
  private getContentType(filename: string): string {
    const ext = path.extname(filename).toLowerCase();
    const contentTypes: {[key: string]: string} = {
      '.html': 'text/html; charset=utf-8',
      '.js': 'application/javascript; charset=utf-8',
      '.css': 'text/css; charset=utf-8',
      '.json': 'application/json; charset=utf-8',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.svg': 'image/svg+xml',
      '.webp': 'image/webp'
    };
    return contentTypes[ext] || 'application/octet-stream';
  }

  // Main deployment method
  async deploy() {
    await this.deployWebsiteFiles();

    return {
      websiteUrl: this.websiteBucket.websiteEndpoint,
      cdnDomain: this.cdn.domainName
    };
  }
}

// Main Deployment Execution
async function main() {
  const infrastructure = new WebappInfrastructure();
  return await infrastructure.deploy();
}

// Export the stack outputs
export = main();