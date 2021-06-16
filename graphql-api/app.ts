import * as fs from 'fs'
import * as _ from 'lodash'
import * as AWS from 'aws-sdk'

import * as neo4j from 'neo4j-driver'
import { makeAugmentedSchema, neo4jgraphql } from 'neo4j-graphql-js'
import { ApolloServer } from 'apollo-server-lambda'

const sm =  new AWS.SecretsManager({region: "eu-west-1"});

const typeDefs = fs.readFileSync('./schema.graphql', 'utf-8');

let driver: neo4j.Driver

// TODO: Move to separate module
const resolvers = {
    ec2__instance: {
        // dummy(parent) {
        //     return `${parent.field1} ${parent.field2}`; // TODO: This only works if field1 and field2 are also requested by the query!
        // },
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

const createHandler = async () => {
    try {
        // TODO: Possible to avoid initializing driver and server every time while also ensuring that a potentially rotated password is used? (use driver.verifyConnectivity ?)
        const neo4jUrl = `bolt://${process.env.neo4j_address}:7687`

        const neo4jSecret = await sm.getSecretValue({SecretId: process.env.neo4j_user_secret_name!}).promise()
        const neo4jPassword = neo4jSecret.SecretString!

        driver = neo4j.driver(
            neo4jUrl,
            neo4j.auth.basic("neo4j", neo4jPassword)
        );

        const server = new ApolloServer({
            schema,
            plugins: [loggingPlugin],
            context: { driver }
        });

        return server.createHandler();
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