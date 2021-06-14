import * as fs from 'fs'
import * as _ from 'lodash'

import * as neo4j from 'neo4j-driver'
import { makeAugmentedSchema, neo4jgraphql } from 'neo4j-graphql-js'
import { ApolloServer } from 'apollo-server-lambda'



// TODO: Read from env vars?
const config = JSON.parse(fs.readFileSync('./config.json', 'utf-8'));

const typeDefs = fs.readFileSync('./schema.graphql', 'utf-8');

const driver = neo4j.driver(
    config.neo4j.url,
    neo4j.auth.basic(config.neo4j.user, config.neo4j.password)
);

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

const schema = makeAugmentedSchema({ typeDefs, resolvers })

const server = new ApolloServer({
    schema,
    context: { driver }
});

const apollo_handler = server.createHandler()

export function handler(event: any, context: any, callback: any): any {
    console.log("received event: " + JSON.stringify(event, null, 2))
    return apollo_handler(event, context, callback)
}
