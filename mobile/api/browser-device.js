"use strict";
const {validOrigin,validBody,configureResponse} = require("../lib/access");
const device = require("../lib/browser-device");
module.exports = function handler(req,res) {
  configureResponse(res);
  if (req.method !== "POST") return res.status(405).json({error:"POST required"});
  if (!validOrigin(req)) return res.status(403).json({error:"Use the Odin Control site"});
  if (!validBody(req,128) || Object.keys(req.body).length!==1)
    return res.status(400).json({error:"Invalid browser request"});
  switch(req.body.action) {
    case "register":
      return res.status(200).json({browser_id:device.enroll(req,res)});
    case "forget":
      device.forget(res);
      return res.status(200).json({forgotten:true});
    default:
      return res.status(400).json({error:"Unknown action"});
  }
};
