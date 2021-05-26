const fs = require('fs');

const { makeAugmentedSchema, neo4jgraphql } = require('neo4j-graphql-js');
const neo4j = require('neo4j-driver')
const { ApolloServer } = require("apollo-server");

// TODO: Read from env vars?
const config = JSON.parse(fs.readFileSync('./config.json'));

const typeDefs = fs.readFileSync('./schema.graphql').toString('UTF-8');

const driver = neo4j.driver(
    config.neo4j.url,
    neo4j.auth.basic(config.neo4j.user, config.neo4j.password)
);

const resolvers = {
    ec2__instance: {
        // dummy(parent) {
        //     return `${parent.field1} ${parent.field2}`; // TODO: This only works if field1 and field2 are also requested by the query!
        // },
    },
    Query: {
        internet_exposed_ec2_instances: async (parent, args, context, info) => {
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
        internet_exposed_elb_loadbalancers: async (parent, args, context, info) => {

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
        internet_exposed_elbv2_loadbalancers: async (parent, args, context, info) => {

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
        sample_my_resources: async (parent, args, context, info) => {
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
        sample_regions_with_ec2: async (parent, args, context, info) => {
            const allRegions = await neo4jgraphql(parent, args, context, info)
            const nonEmptyRegions = allRegions.filter(f => f.ec2__instances.length > 0)

            return nonEmptyRegions
        }
    }
};

const schema = makeAugmentedSchema({ typeDefs, resolvers })

const server = new ApolloServer({
    schema,
    context: { driver }
});

server.listen(4000).then(({ url }) => {
    console.log(`Online at ${url}`)
});