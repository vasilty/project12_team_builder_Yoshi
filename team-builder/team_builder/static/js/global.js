$( document ).ready(function() {

  $('textarea').autogrow({onInitialize: true});


  // //Cloner for infinite input lists
  // $(".circle--clone--list").on("click", ".circle--clone--add", function(){
  //   var parent = $(this).parent("li");
  //   var copy = parent.clone();
  //   parent.after(copy);
  //   copy.find("input, textarea, select").val("");
  //   copy.find("*:first-child").focus();
  // });
  //
  // $(".circle--clone--list").on("click", "li:not(:only-child) .circle--clone--remove", function(){
  //   var parent = $(this).parent("li");
  //   parent.remove();
  // });

  // Adds class to selected item
  $(".circle--pill--list a").click(function() {
    $(".circle--pill--list a").removeClass("selected");
    $(this).addClass("selected");
  });

  // Adds class to parent div of select menu
  $(".circle--select select").focus(function(){
   $(this).parent().addClass("focus");
   }).blur(function(){
     $(this).parent().removeClass("focus");
   });

  // Clickable table row
  $(".clickable-row").click(function() {
      var link = $(this).data("href");
      var target = $(this).data("target");

      if ($(this).attr("data-target")) {
        window.open(link, target);
      }
      else {
        window.open(link, "_self");
      }
  });

  // Non-clickable table row
  $(".nonclickable-cell").click(function(event) {
      event.stopPropagation();
  });

  // Custom File Inputs
  var input = $(".circle--input--file");
  var text = input.data("text");
  var state = input.data("state");
  input.wrap(function() {
    return "<a class='button " + state + "'>" + text + "</div>";
  });

  // Get CSRF token
  function getCookie(name) {
      var cookieValue = null;
      if (document.cookie && document.cookie !== '') {
          var cookies = document.cookie.split(';');
          for (var i = 0; i < cookies.length; i++) {
              var cookie = jQuery.trim(cookies[i]);
              // Does this cookie string begin with the name we want?
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
                  cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                  break;
              }
          }
      }
      return cookieValue;
  }
  var csrftoken = getCookie('csrftoken');

  function csrfSafeMethod(method) {
  // these HTTP methods do not require CSRF protection
      return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  }

  // Confirmation for project deletion
  $("#delete-project-button").on('click', function () {
      event.preventDefault();
      var project = $('.circle--article--title').text();
      console.log(project);
      swal({
          title: "Are you sure?",
          text: 'You are going to delete the "' + project + '" project.',
          type: "warning",
          showCancelButton: true,
          confirmButtonText: "Delete",
          closeOnConfirm: true,
          confirmButtonColor: "#689b98",
          allowOutsideClick: true
          },
          function () {
              $.ajaxSetup({
                  beforeSend: function(xhr, settings) {
                      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                          xhr.setRequestHeader("X-CSRFToken", csrftoken);
                      }
                  }
              });

              $.post(this.href, function(data) {
                  window.location.href = data.url;
              }).fail(function() {

              });
          }.bind(this)
      )
  });

  // Confirmation for application status change
  $(".application-accept-button, .application-reject-button").on('click', function (event) {
      event.preventDefault();
      var form = $(this).parent();
      var href = form.attr('action');
      var action = href.split('?');
      action = action[0];
      action = action.split('/');
      action = action[action.length-1];
      var applicant = form.parent().siblings('.application-applicant-project').children('h3').text();
      var project = form.parent().siblings('.application-applicant-project').children('p').text();
      var position = form.parent().siblings('.application-position').children('span').text();
      var explanation = "You are going to " + action + ' ' + applicant + " for a " + position + ' position in the ' + '"' + project + '"' + '.';
      swal({
          title: "Are you sure?" ,
          text: explanation,
          type: "warning",
          showCancelButton: true,
          confirmButtonText: "Yes",
          closeOnConfirm: true,
          confirmButtonColor: "#689b98",
          allowOutsideClick: true
          },
          function () {
              form.submit();
          }.bind(this)
      );
  });

  // Hide flash message on click
  $('.alert').on('click', function(){
      $(this).hide("slow");
  });

  function notifyMe(title, message) {
      // Let's check if the browser supports notifications
      if (!("Notification" in window)) {
        alert("This browser does not support desktop notification");
      }

      // Let's check whether notification permissions have already been granted
      else if (Notification.permission === "granted") {
        // If it's okay let's create a notification
        var notification = new Notification(title, {
              body: message
              });
      }

      // Otherwise, we need to ask the user for permission
      else if (Notification.permission !== 'denied') {
        Notification.requestPermission(function (permission) {
          // If the user accepts, let's create a notification
          if (permission === "granted") {
            var notification = new Notification(title, {
              body: message
              });
          }
        });
      }

      // At last, if the user has denied notifications, and you
      // want to be respectful there is no need to bother them any more.
  }

  // Show push notification to users
  function pusher(userId) {
    // Pusher related code
    var pusher = new Pusher('c2eac3b62fd45a991432', {
      cluster: 'eu'
    });
    var notificationsChannel = pusher.subscribe('team-builder-' + userId);

    notificationsChannel.bind('new_notification', function(notification) {
      var title = notification.title;
      var message = notification.message;
      notifyMe(title, message);
    });
  }
  if (userId) {pusher(userId)}


    $("#info").hover(function() {
        $(this).attr('title', 'Markdown formatting can be used for this field.');
    });

    $("#info").on('click', function() {
        $('#lightbox').show();
    });

    $('#close-icon').on('click', function(e){
        $('#lightbox').hide();
    });


});
