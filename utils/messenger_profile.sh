curl -X POST -H "Content-Type: application/json" -d '{
"get_started" : {"payload": "get_started"},
"persistent_menu":[
  {
    "locale":"default",
    "composer_input_disabled": false,
    "call_to_actions":[
      {
        "type":"postback",
        "title":"查詢公車",
        "payload":"lookup_by_id"
      },
      {
        "title":"Categories",
        "type":"nested",
        "call_to_actions":[
          {
            "title":"PHP",
            "type":"postback",
            "payload":"CAT_PHP_PAYLOAD"
          },
          {
            "title":"Database",
            "type":"postback",
            "payload":"CAT_DB_PAYLOAD"
          },
          {
            "title":"Python",
            "type":"postback",
            "payload":"CAT_PYTHON_PAYLOAD"
          }
        ]
      },
      {
        "type":"web_url",
        "title":"Visit Website",
        "url":"http://thedebuggers.com/"
      }
    ]
  }
]
}' "https://graph.facebook.com/v2.6/me/messenger_profile?access_token=$PAGE_ACCESS_TOKEN"
