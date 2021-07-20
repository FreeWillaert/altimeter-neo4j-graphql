import * as fs from 'fs'
import * as _ from 'lodash'
import * as AWS from 'aws-sdk'

import * as neo4j from 'neo4j-driver'
import { makeAugmentedSchema, neo4jgraphql } from 'neo4j-graphql-js'
import { Config, decorateWithLogger } from 'apollo-server'
import { ApolloServer } from 'apollo-server-lambda'

const sm =  new AWS.SecretsManager({region: "eu-west-1"})

const typeDefs = fs.readFileSync('./schema.graphql', 'utf-8')

let driver: neo4j.Driver
let theHandler: any = null

// TODO: Get account names json through http request
const accountNames:any = JSON.parse(fs.readFileSync('./accounts.json','utf-8'))

function getNameFromTags (parent:any) {
    {
        if(!parent.tags) return "[need tags]"

        const nameTag = parent.tags.filter((t:any) => t["alti__key"] === "Name")[0]
        if(!nameTag) return "[need Name tag]"
        
        const nameTagValue = nameTag["alti__value"]
        if(!nameTagValue) return "[need Name tag value]"
        return nameTagValue
    }
}

// TODO: Move to separate module
const resolvers = {

    alti__metadata: {
        // TODO: Use full custom resolver so that alti__start/end_time doesn't need to be requested by client.
        start_timestamp_utc(parent:any) {
            return new Date(parent.alti__start_time*1000).toISOString()
        },
        end_timestamp_utc(parent:any) {
            return new Date(parent.alti__end_time*1000).toISOString()
        }
    },
    aws__account: {
        name(parent:any) {
            return (parent.alti__account_id) ? accountNames[parent.alti__account_id] || `[${parent.alti__account_id} UNKNOWN]` : "[need alti__account_id]"
        }
    },
    ec2__vpc: {
        name: getNameFromTags
    },
    ec2__subnet: {
        name: getNameFromTags
    },
    Query: {
        internet_exposed_ec2_instances: async (parent:any, args:any, context:any, info:any) => {
            const internet_exposed_filter = {
                OR: [
                    {
                        security_groups_some: {
                            ingress_rules_some: {
                                ip_ranges_some: {
                                    alti__cidr_ip_starts_with: '0.0.0.0'
                                }
                            }
                        }
                    },
                    {
                        network_interfaces_some: {
                            security_groups_some: {
                                ingress_rules_some: {
                                    ip_ranges_some: {
                                        alti__cidr_ip_starts_with: "0.0.0.0"
                                    }
                                }
                            }
                        }
                    }
                ]
            }

            args.filter = (args.filter) ? { AND: [ args.filter, internet_exposed_filter]} : internet_exposed_filter

            return await neo4jgraphql(parent, args, context, info)
        },
        internet_exposed_elb_loadbalancers: async (parent:any, args:any, context:any, info:any) => {

            const internet_exposed_filter = {
                AND: [
                    { alti__scheme: "internet-facing" },
                    {
                        security_groups_some: {
                            ingress_rules_some: {
                                ip_ranges_some: {
                                    alti__cidr_ip_starts_with: '0.0.0.0'
                                }
                            }
                        }
                    }
                ]
            }

            args.filter = (args.filter) ? { AND: [ args.filter, internet_exposed_filter]} : internet_exposed_filter

            return await neo4jgraphql(parent, args, context, info)
        },
        internet_exposed_elbv2_loadbalancers: async (parent:any, args:any, context:any, info:any) => {

            const internet_exposed_filter = {
                AND: [
                    { alti__scheme: "internet-facing" },
                    {
                        security_groups_some: {
                            ingress_rules_some: {
                                ip_ranges_some: {
                                    alti__cidr_ip_starts_with: '0.0.0.0'
                                }
                            }
                        }
                    }
                ]
            }

            args.filter = (args.filter) ? { AND: [ args.filter, internet_exposed_filter]} : internet_exposed_filter

            return await neo4jgraphql(parent, args, context, info)
        },
        sample_my_resources: async (parent:any, args:any, context:any, info:any) => {
            let session
            try {
                session = driver.session()
                const result = await session.run('MATCH (n:Resource) RETURN n')
                const fields = result.records.map(record => _.merge({ id: +record.get(0).identity }, record.get(0).properties))
                return fields
            } finally {
                if (session) await session.close()
            }
        },
        sample_regions_with_ec2: async (parent:any, args:any, context:any, info:any) => {
            const allRegions = await neo4jgraphql(parent, args, context, info)
            const nonEmptyRegions = allRegions.filter((f:any) => f.ec2__instances.length > 0)

            return nonEmptyRegions
        }
    }
};

const loggingPlugin = {

    // Fires whenever a GraphQL request is received from a client.
    requestDidStart(requestContext:any) {
      console.log('Request started! Query:\n' +
        requestContext.request.query);
  
      return {
  
        // Fires whenever Apollo Server will parse a GraphQL
        // request to create its associated document AST.
        parsingDidStart(requestContext:any) {
            console.log('Parsing started!');
        },
  
        // Fires whenever Apollo Server will validate a
        // request's document AST against your GraphQL schema.
        validationDidStart(requestContext:any) {
            console.log('Validation started:');
        },
  
        // Fires when Apollo Server encounters errors while parsing, 
        // validating, or executing a GraphQL operation.
        didEncounterErrors(requestContext:any) {
            console.log('Did encounter errors.');
            console.log(JSON.stringify(requestContext));
        },              
        // Fires whenever Apollo Server is about to send a response 
        // for a GraphQL operation, 
        // even if the GraphQL operation encounters one or more errors.
        willSendResponse(requestContext:any) {
            console.log('Will send response.');
            console.log(JSON.stringify(requestContext));
          },      
        }        
    },
  };

const schema = makeAugmentedSchema({ typeDefs, resolvers })

export async function createServerConfig(): Promise<Config> {
    // TODO: Possible to avoid initializing driver and server every time while also ensuring that a potentially rotated password is used? (use driver.verifyConnectivity ?)
    const neo4jUrl = `bolt://${process.env.neo4j_address}:7687`

    const neo4jSecret = await sm.getSecretValue({SecretId: process.env.neo4j_user_secret_name!}).promise()
    const neo4jPassword = neo4jSecret.SecretString!

    driver = neo4j.driver(
        neo4jUrl,
        neo4j.auth.basic("neo4j", neo4jPassword)
    );

    return {
        schema,
        plugins: [loggingPlugin],
        context: { driver },        
        playground: {
            endpoint: "/prod/graphql",
            settings: {
                'schema.polling.enable': false
            }
          }
    }
}

async function getCurrentHandler(): Promise<any> {
    if(!theHandler) return null // upon initialization, just return null and a handler will be created

    // from here on, theHandler is not null so it has been initialized; as long as the driver says we're good, we continue to use the existing handler
    try {
        const serverInfo = await driver.verifyConnectivity({database: "neo4j"});
        console.log("neo4j server info: ", serverInfo)
        return theHandler
    } catch(error) {
        // handler was initialized before but driver can no longer connect to neo4j, so return null and have a new handler created 
        console.log("driver no longer connected - will try to establish a new connection");
        return null
    }    
}

const createHandler = async () => {
    try {
        let handler = await getCurrentHandler()

        if(!handler) {
            const serverConfig = await createServerConfig()
            const server = new ApolloServer(serverConfig); // This is the 'lambda' ApolloServer!
            handler = server.createHandler({
                cors: {
                    origin: '*'
                }
            });
            theHandler = handler
        }

        return handler
    }
    catch(error) {
        console.error(error)
    }
 };
 
 export const handler = (event: any, context: any, callback: any) => {
    console.log("received event: " + JSON.stringify(event, null, 2))
    createHandler().then(
        (handler: any) => handler(event, context, callback)
    ).catch((error:any) => console.error(error))

 };