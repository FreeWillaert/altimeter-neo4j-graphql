import fs from 'fs'
import { createServerConfig } from './app'

import {ApolloServer} from 'apollo-server'

// app.handler(event,{},(data:any)=>console.log(data))
(async () => {
    const config = JSON.parse(fs.readFileSync('./config.json', 'utf-8'))
    const event = JSON.parse(fs.readFileSync('./event.json', 'utf-8'))
    
    process.env.neo4j_address = config.neo4j.address
    process.env.neo4j_user_secret_name = "secret-altimeter-neo4j-user"

    const serverConfig = await createServerConfig()

    const server = new ApolloServer(serverConfig)

    server.listen(4000).then(({ url }) => {
        console.log(`Online at ${url}`)
    });
})()

