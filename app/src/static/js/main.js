$(function () {

  function update_iteration_speed() {
    $.ajax("current_speed.json")
      .done(function(data) {
        $("#iteration-speed").text(data['current_speed']);
      });
  }

  while (true) {
    setTimeout(update_iteration_speed, 100);
  }

});
