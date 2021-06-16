import fs from 'fs'
import * as app from './app'

const config = JSON.parse(fs.readFileSync('./config.json', 'utf-8'));
const event = JSON.parse(fs.readFileSync('./event.json', 'utf-8'));

process.env.neo4j_address = config.neo4j.address
process.env.neo4j_user_secret_name = "secret-altimeter-neo4j-user"

app.handler(event,{},(data:any)=>console.log(data))
