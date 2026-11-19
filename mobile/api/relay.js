"use strict";
const {authorized,validOrigin,validBody,configureResponse}=require("../lib/access");
const relay=require("../lib/relay");

module.exports=async function handler(req,res){
  configureResponse(res);
  const device=relay.deviceAuthorized(req);
  const owner=authorized(req)&&validOrigin(req);
  if(!device&&!owner)return res.status(403).json({error:"Pairing is not configured or access denied"});
  if(!process.env.BLOB_READ_WRITE_TOKEN&&!process.env.VERCEL_OIDC_TOKEN)
    return res.status(503).json({error:"Private relay storage is not configured"});
  if(req.method!=="GET"&&req.method!=="POST"){
    res.setHeader("Allow","GET, POST");
    return res.status(405).json({error:"Unsupported method"});
  }
  if(req.method==="POST"&&!validBody(req,6000))
    return res.status(400).json({error:"Invalid message format"});
  try {
    if(req.method==="GET"){
      const all=await relay.loadEvents();
      const history=relay.view(all,owner?"iphone":"odin");
      return res.status(200).json({
        source:"private-odin-relay",connected:true,
        messages:history.slice(-60),
        unread:owner?history.filter(x=>x.sender==="odin"&&x.status==="queued").length:
          history.filter(x=>x.to==="odin"&&x.status==="queued").length
      });
    }
    const body=req.body;
    if(owner&&!device&&relay.validMessage(body)){
      const entry=await relay.recordEvent({
        kind:"message",sender:"iphone",to:"odin",text:body.text.trim()
      });
      return res.status(202).json({id:entry.id,status:"queued",at:entry.at});
    }
    if(device&&relay.validReceipt(body)){
      const all=await relay.loadEvents();
      if(!all.some(x=>x.kind==="message"&&x.id===body.for&&x.to==="odin"))
        return res.status(404).json({error:"Original message unavailable"});
      const entry=await relay.recordEvent({
        kind:"receipt",sender:"odin",for:body.for,state:body.state
      });
      return res.status(201).json({id:entry.id,status:body.state,at:entry.at});
    }
    if(device&&relay.validReply(body)){
      const all=await relay.loadEvents();
      if(!all.some(x=>x.kind==="message"&&x.id===body.for&&x.to==="odin"))
        return res.status(404).json({error:"Original message unavailable"});
      if(all.some(x=>x.kind==="message"&&x.reply_to===body.for&&x.sender==="odin"))
        return res.status(409).json({error:"Already replied"});
      const entry=await relay.recordEvent({
        kind:"message",sender:"odin",to:"iphone",reply_to:body.for,
        text:body.text.trim()
      });
      return res.status(201).json({id:entry.id,status:"replied",at:entry.at});
    }
    return res.status(400).json({error:"Message action not allowed"});
  }catch{
    return res.status(503).json({error:"Private relay storage temporarily unavailable"});
  }
};