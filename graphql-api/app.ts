import * as fs from 'fs'
import * as neo4j from 'neo4j-driver'


// const { ApolloServer } = require("apollo-server");

// TODO: Read from env vars?
const config = JSON.parse(fs.readFileSync('./config.json', 'utf-8'));

const typeDefs = fs.readFileSync('./schema.graphql', 'utf-8');

const driver = neo4j.driver(
    config.neo4j.url,
    neo4j.auth.basic(config.neo4j.user, config.neo4j.password)
);

export function handler(): string {
  return `Hello world!`;
}