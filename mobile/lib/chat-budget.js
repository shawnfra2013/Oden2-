"use strict";
const {withClient}=require("./wake");
const {createHash}=require("node:crypto");
const reserveScript=`
  if redis.call('EXISTS', KEYS[1]) == 1 then return 'duplicate' end
  local count = tonumber(redis.call('GET', KEYS[2]) or '0')
  if count >= tonumber(ARGV[1]) then return 'limit' end
  redis.call('SET', KEYS[1], '1', 'EX', 172800)
  redis.call('INCR', KEYS[2])
  redis.call('EXPIRE', KEYS[2], 172800)
  return 'reserved'`;
function dailyLimit(){
  const value=process.env.ODIN_CLOUD_CHAT_DAILY_LIMIT || "2";
  return /^([1-9]|[1-9][0-9]{1,2})$/.test(value)?Number(value):0;
}
function configured(){
  return Boolean(dailyLimit() && process.env.ODIN_WAKE_REDIS_URL?.startsWith("rediss://"));
}
async function reserve(id){
  const day=new Date().toISOString().slice(0,10);
  if(typeof id!=="string" || !/^\d{4}-\d{2}-\d{2}:[0-9a-f]{32}$/.test(id) || !id.startsWith(day+":"))return "expired";
  const digest=createHash("sha256").update(id).digest("hex");
  return withClient(client=>client.eval(reserveScript,{
    keys:["odin:chat:{budget}:turn:"+digest,"odin:chat:{budget}:day:"+day],
    arguments:[String(dailyLimit())]
  }));
}
module.exports={reserve,configured};
