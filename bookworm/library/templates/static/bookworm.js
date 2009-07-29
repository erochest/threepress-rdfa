jQuery(document).ready(function() {
        //        $("#bw-upload-box").hide();

        $('#bw-upload-link').hover(function() {
                $("#bw-upload-box").slideDown('fast');
            },
            function() {}
            );
        $('#bw-shell-table').hover(function() {
                $("#bw-upload-box").slideUp('fast');
            },
            function() {} );

        $('.bw-what-is-openid-link').click(function() {
                $("#bw-what-is-openid").fadeIn('normal');
            }
            );
        $('#bw-search-lang-change').click(function() {
                $("#bw-search-lang-selection").fadeIn('normal');
            }
            );
        $('#bw-search-lang-hide').click(function() {
                $("#bw-search-lang-selection").fadeOut('normal');
            }
            );

        $('#bw-feedbooks-toggle').toggle(function() {
                                             $('#bw-feedbooks').fadeIn('normal');
                                             $('#bw-feedbooks-toggle').text('Hide');
                                         },
                                         function() {
                                             $('#bw-feedbooks').fadeOut('normal');
                                             $('#bw-feedbooks-toggle').text('Show');
                                         }
                                        );

        var main_text = $('#bw-book-content');
        var current_size = get_font_sizing(main_text);
        if (current_size != null) {
            var num = get_font_num(current_size);
            var unit = get_font_unit(current_size);
        }

        // Font-size changer
        $("a.bw-font-size-changer").click(function(){

            // Font threshold should be toggled here
            if (this.id == 'bw-increase-font'){
                num = num * 1.2;
            } else if (this.id == 'bw-decrease-font'){
                num = num / 1.2;
            }
            num = round_to(num, 5);
            update_font_size(main_text, num, unit);
            jQuery.post('/account/profile/change-font-size/' + num + unit + '/');
            return false;
        });

        // Font-family changer
        $("a.bw-font-family-changer").click(function(){
            var font = '';
            // Font threshold should be toggled here
            if (this.id == 'bw-serif-font'){
                font = 'serif';
            } else if (this.id == 'bw-sans-serif-font'){
                font = 'sans-serif';
            }
            update_font_family(main_text, font);
            jQuery.post('/account/profile/change-font-family/' + font + '/');
            return false;
        });


});

function round_to(n, sig) {
    var mult = Math.pow(10, sig - Math.floor(Math.log(n) / Math.LN10) - 1);
    return Math.round(n * mult) / mult;
}

function get_font_sizing(mainText) {
    return  mainText.css('font-size');
}

function get_font_num(current_size) {
    return parseFloat(current_size, 10);
}

function get_font_unit(current_size) {
    return current_size.slice(-2);
}

function update_font_size(el, num, unit) {
    el.css('font-size', num + unit);
    el.find('p').css('font-size', num + unit);
    el.find('div').css('font-size', num + unit);
}

function update_font_family(el, font) {
    el.css('font-family', font);
    el.find('p').css('font-family', font);
    el.find('div').css('font-family', font);
}
