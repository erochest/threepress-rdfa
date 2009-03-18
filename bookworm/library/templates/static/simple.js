    $('#bw-shell-left').click(function() {
      if ($('span.bw-previous:first a').attr('href') != null) {
        document.location.href = $('span.bw-previous:first a').attr('href');
      }
    });
    /* Show directional clue when turning back */
    $('#bw-shell-left').hover(function() {
      $('#bw-left-arrow').fadeIn(2000);
    },
    function() {
      $('#bw-left-arrow').fadeOut('fast');
    }
    );

    /* Show directional clue when turning forward */
    $('#bw-shell-right').hover(function() {
      $('#bw-right-arrow').fadeIn(2000);
    },
    function() {
      $('#bw-right-arrow').fadeOut('fast');
    }
    );

    $('#bw-shell-right').click(function() {
      if ($('span.bw-next:first a').attr('href') != null) {
        document.location.href = $('span.bw-next:first a').attr('href');
      }
    });
