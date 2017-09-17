$(() => {
  let timeoutID;
  let timeoutInterval = 100;
  const serverWSHandler = "ws://localhost:8000/feed";
  const ws = new WebSocket(serverWSHandler);
  ws.onopen = event => {
    console.log("onopen with ", event);
  };
  ws.onclose = event => {
    console.log("onclose with ", event);
  };
  ws.onerror = event => {
    console.error("onerror with ", event);
  };
  ws.onmessage = event => {
    const data = JSON.parse(event.data);
    console.log(data);
    timeoutID = window.setTimeout(sendMessage, timeoutInterval);
  };

  function sendMessage() {
    if (ws.readyState === 1) {
      ws.send("OK");
    }
    window.clearTimeout(timeoutID);
  };

  function closeWS() {
    if (ws.readyState === 1) {
      ws.close();
    }
  };
});
