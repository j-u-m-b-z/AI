import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as mime from "mime-types";
import * as fs from "fs";
import * as path from "path";

// Configure AWS Provider for Singapore region
const awsProvider = new aws.Provider("aws-provider", {
    region: "ap-southeast-1"
});

// Configuration with CORRECTED build path
const config = new pulumi.Config();
const angularDistPath = "../dist/human-image-validation-webapp"; // Corrected path
const appName = "human-image-validation-app";
const accountId = "224861234701";

// Create an S3 bucket for the website
const siteBucket = new aws.s3.Bucket(`${appName}-bucket`, {
    forceDestroy: true,
}, { provider: awsProvider });

// Create a CloudFront origin access identity
const originAccessIdentity = new aws.cloudfront.OriginAccessIdentity(`${appName}-oai`, {
    comment: "OAI for S3 bucket access",
}, { provider: awsProvider });

// More permissive bucket policy that allows CloudFront OAI to access objects
const bucketPolicy = new aws.s3.BucketPolicy(`${appName}-bucket-policy`, {
    bucket: siteBucket.id,
    policy: pulumi.all([siteBucket.arn, originAccessIdentity.iamArn]).apply(([bucketArn, oaiArn]) => JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Sid: "1",
            Effect: "Allow",
            Principal: {
                AWS: oaiArn
            },
            Action: "s3:GetObject",
            Resource: `${bucketArn}/*`
        }]
    }))
}, { provider: awsProvider });

// Helper function to recursively upload directory contents
function uploadDirectory(directoryPath: string, bucketName: pulumi.Output<string>, provider: aws.Provider) {
    console.log(`Attempting to upload files from: ${directoryPath}`);
    console.log(`Directory exists: ${fs.existsSync(directoryPath)}`);
    
    if (!fs.existsSync(directoryPath)) {
        console.error(`Directory not found: ${directoryPath}`);
        return;
    }
    
    const files = fs.readdirSync(directoryPath);
    console.log(`Files found: ${files.length}`);
    console.log(`First few files: ${files.slice(0, 5).join(', ')}`);
    
    for (const file of files) {
        const filePath = path.join(directoryPath, file);
        const stat = fs.statSync(filePath);
        
        if (stat.isDirectory()) {
            uploadDirectory(filePath, bucketName, provider);
        } else {
            const relativeFilePath = path.relative(angularDistPath, filePath);
            const contentType = mime.lookup(filePath) || "application/octet-stream";
            
            console.log(`Uploading: ${relativeFilePath} (${contentType})`);
            
            new aws.s3.BucketObject(
                `${appName}-${relativeFilePath.replace(/[^a-zA-Z0-9]/g, "-")}`,
                {
                    bucket: bucketName,
                    key: relativeFilePath,
                    source: new pulumi.asset.FileAsset(filePath),
                    contentType: contentType,
                },
                { provider }
            );
        }
    }
}

// Create CloudFront distribution with OAI
const distribution = new aws.cloudfront.Distribution(`${appName}-cdn`, {
    enabled: true,
    waitForDeployment: true,
    
    origins: [{
        originId: siteBucket.id.apply(id => id),
        domainName: siteBucket.bucketRegionalDomainName,
        s3OriginConfig: {
            originAccessIdentity: originAccessIdentity.cloudfrontAccessIdentityPath,
        },
    }],
    
    defaultRootObject: "index.html",
    
    defaultCacheBehavior: {
        targetOriginId: siteBucket.id.apply(id => id),
        viewerProtocolPolicy: "redirect-to-https",
        allowedMethods: ["GET", "HEAD", "OPTIONS"],
        cachedMethods: ["GET", "HEAD", "OPTIONS"],
        forwardedValues: {
            queryString: false,
            cookies: { forward: "none" },
        },
        minTtl: 0,
        defaultTtl: 86400,
        maxTtl: 31536000,
        compress: true,
    },
    
    // SPA routing support
    customErrorResponses: [
        {
            errorCode: 404,
            responseCode: 200,
            responsePagePath: "/index.html",
        },
        {
            errorCode: 403,
            responseCode: 200,
            responsePagePath: "/index.html",
        }
    ],
    
    priceClass: "PriceClass_All",
    
    restrictions: {
        geoRestriction: {
            restrictionType: "none",
        },
    },
    
    viewerCertificate: {
        cloudfrontDefaultCertificate: true,
    },
}, { provider: awsProvider });

// Upload Angular app to S3
if (fs.existsSync(angularDistPath)) {
    uploadDirectory(angularDistPath, siteBucket.id, awsProvider);
    console.log(`Upload completed to bucket ${siteBucket.id}`);
} else {
    console.error(`Angular build directory not found: ${angularDistPath}`);
    console.log(`Current directory: ${process.cwd()}`);
    console.log(`Looking for: ${path.resolve(angularDistPath)}`);
}

// Output the CloudFront URL
export const region = "ap-southeast-1";
export const bucketName = siteBucket.id;
export const cloudfrontDomain = distribution.domainName;
export const cloudfrontUrl = pulumi.interpolate`https://${distribution.domainName}`;